"""The pages people actually see.

home            works out who you are and sends you to your page
student_home    the student's list of deadlines
supervisor_home the supervisor's table of all their students
coordinator_home every supervisor and their students
export_csv      the same table as a spreadsheet file
"""
import csv

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone

from progress.models import Deliverable, Submission
from risk.models import RiskScore


def role_required(role):
    """Only lets the right kind of user open a page. Anyone else gets a 403 (not allowed)."""
    def decorator(view):
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


@login_required
def home(request):
    if request.user.is_student:
        return redirect("student_home")
    if request.user.is_supervisor:
        return redirect("supervisor_home")
    return redirect("coordinator_home")


def timeline_for(student, now=None):
    """Goes through every deliverable and works out where this student stands on each one."""
    now = now or timezone.now()
    submissions = {s.deliverable_id: s for s in Submission.objects.filter(student=student).order_by("submitted_at")}
    rows = []
    for d in Deliverable.objects.all():
        sub = submissions.get(d.id)
        days_left = (d.due_at - now).days
        if sub:
            late = sub.days_late()
            status, label = ("late", f"Submitted {late} days late") if late else ("done", "Submitted")
        elif d.due_at < now:
            status, label = "missing", "Missing"
        elif days_left <= 7:
            status, label = "soon", f"Due in {days_left} days"
        else:
            status, label = "upcoming", f"Due in {days_left} days"
        rows.append({"deliverable": d, "submission": sub, "status": status, "label": label})
    return rows


@role_required("student")
def student_home(request):
    rows = timeline_for(request.user)
    latest = RiskScore.objects.filter(student=request.user).first()
    return render(request, "dashboard/student_home.html", {"rows": rows, "risk": latest})


def summary_for(student, now, due_count):
    """One line about a student: their score, how much is in, how much is missing, last meeting."""
    rows = timeline_for(student, now)
    return {
        "user": student,
        "risk": RiskScore.objects.filter(student=student).first(),
        # submitted counts work for deliverables already due, early uploads are shown separately
        "submitted": sum(1 for r in rows if r["status"] in ("done", "late") and r["deliverable"].due_at < now),
        "early": sum(1 for r in rows if r["status"] in ("done", "late") and r["deliverable"].due_at >= now),
        "missing": sum(1 for r in rows if r["status"] == "missing"),
        "due_count": due_count,
        "last_meeting": student.meetings.order_by("-held_on").first(),
    }


@role_required("supervisor")
def supervisor_home(request):
    now = timezone.now()
    due_count = Deliverable.objects.filter(due_at__lt=now).count()
    students = [summary_for(s, now, due_count) for s in request.user.students.order_by("last_name", "first_name")]
    # how many students are green, amber and red right now, for the summary and the chart
    counts = {"green": 0, "amber": 0, "red": 0, "none": 0}
    for s in students:
        counts[s["risk"].status if s["risk"] else "none"] += 1
    return render(request, "dashboard/supervisor_home.html", {"students": students, "counts": counts})


@role_required("coordinator")
def coordinator_home(request):
    """The coordinator sees every supervisor with their students and colours."""
    from accounts.models import User
    groups = []
    for supervisor in User.objects.filter(role="supervisor").order_by("last_name", "first_name"):
        students = supervisor.students.order_by("last_name", "first_name")
        counts = {"green": 0, "amber": 0, "red": 0, "none": 0}
        rows = []
        for student in students:
            risk = RiskScore.objects.filter(student=student).first()
            counts[risk.status if risk else "none"] += 1
            rows.append({"user": student, "risk": risk})
        groups.append({"supervisor": supervisor, "rows": rows, "counts": counts, "total": len(rows)})
    return render(request, "dashboard/coordinator_home.html", {"groups": groups})


@login_required
def export_csv(request):
    """Downloads the student table as a csv file, which opens in Excel.

    A supervisor gets their own students, the coordinator gets everyone. Students cannot use it.
    """
    from accounts.models import User
    if request.user.is_supervisor:
        students = request.user.students.all()
    elif request.user.is_coordinator:
        students = User.objects.filter(role="student")
    else:
        raise PermissionDenied
    now = timezone.now()
    due_count = Deliverable.objects.filter(due_at__lt=now).count()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="clptrack_{now:%Y-%m-%d}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Student ID", "Name", "Section", "Supervisor", "Score", "Status",
                     "Submitted", "Early", "Missing", "Due so far", "Last meeting"])
    for student in students.order_by("last_name", "first_name"):
        row = summary_for(student, now, due_count)
        writer.writerow([
            student.student_id,
            student.get_full_name() or student.username,
            student.section,
            student.supervisor.get_full_name() if student.supervisor else "",
            row["risk"].score if row["risk"] else "",
            row["risk"].status if row["risk"] else "not scored",
            row["submitted"],
            row["early"],
            row["missing"],
            due_count,
            row["last_meeting"].held_on if row["last_meeting"] else "none",
        ])
    return response
