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

from datetime import timedelta

from notifications.models import NotificationLog
from progress.models import Action, Deliverable, Meeting, Submission
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
    now = timezone.now()
    rows = timeline_for(request.user, now)
    latest = RiskScore.objects.filter(student=request.user).first()
    upcoming = [r for r in rows if r["status"] in ("soon", "upcoming")]
    next_row = None
    if upcoming:
        next_row = dict(upcoming[0], days_left=(upcoming[0]["deliverable"].due_at - now).days)
    return render(request, "dashboard/student_home.html", {
        "rows": rows, "risk": latest, "next_row": next_row, "steps": next_steps(request.user, rows, now),
        "submitted_count": sum(1 for r in rows if r["status"] in ("done", "late")),
        "missing_count": sum(1 for r in rows if r["status"] == "missing"),
    })


def summary_for(student, now, due_count):
    """One line about a student: their score, how much is in, how much is missing, last meeting."""
    rows = timeline_for(student, now)
    latest = RiskScore.objects.filter(student=student).first()
    week_ago = RiskScore.objects.filter(student=student, scored_on__lte=now.date() - timedelta(days=7)).first()
    trend = (latest.score - week_ago.score) if latest and week_ago else None
    return {
        "user": student,
        "risk": latest,
        "trend": trend,
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
    return render(request, "dashboard/supervisor_home.html", {
        "students": students, "counts": counts,
        "activity": recent_activity(request.user, now),
        "emails": NotificationLog.objects.filter(recipient=request.user).order_by("-sent_at")[:8],
    })


def recent_activity(supervisor, now, days=7):
    """What this supervisor's students did in the last week: uploads and meetings, newest first."""
    since = now - timedelta(days=days)
    items = []
    for sub in Submission.objects.filter(student__supervisor=supervisor, submitted_at__gte=since).select_related("student", "deliverable"):
        items.append({"when": sub.submitted_at, "student": sub.student, "text": f"uploaded {sub.deliverable.title}"})
    for m in Meeting.objects.filter(student__supervisor=supervisor, created_at__gte=since).select_related("student"):
        items.append({"when": m.created_at, "student": m.student, "text": f"recorded a meeting held on {m.held_on:%-d %B}"})
    return sorted(items, key=lambda i: i["when"], reverse=True)[:10]


def next_steps(student, rows, now):
    """Plain words for the student: what would bring the score down, most urgent first."""
    steps = []
    for r in rows:
        if r["status"] == "missing":
            days = (now - r["deliverable"].due_at).days
            steps.append((0, f"Upload {r['deliverable'].title}, it is {days} day{'s' if days != 1 else ''} overdue", r["deliverable"]))
    last = Meeting.objects.filter(student=student).order_by("-held_on").first()
    gap = (now.date() - last.held_on).days if last else None
    if last is None:
        steps.append((1, "Record your first meeting with your supervisor", None))
    elif gap > 7:
        steps.append((1, f"Record your latest meeting, the last one recorded was {gap} days ago", None))
    open_actions = Action.objects.filter(meeting__student=student, done=False).count()
    if open_actions:
        steps.append((2, f"{open_actions} agreed action{'s are' if open_actions != 1 else ' is'} still open, tick them off when done", None))
    for r in rows:
        if r["status"] == "soon":
            steps.append((3, f"{r['deliverable'].title} is due in {(r['deliverable'].due_at - now).days} days and nothing is uploaded yet", r["deliverable"]))
            break
    return [{"text": t, "deliverable": d} for _, t, d in sorted(steps, key=lambda x: x[0])]


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
