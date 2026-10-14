"""The pages people actually see, and the counting behind them.

home             works out who you are and sends you to your page
student_home     the student's deadlines, what to do next, feedback and score
supervisor_home  the supervisor's table of their students, the week's activity and alerts
coordinator_home the whole cohort with statistics, then every student under their supervisor
export_csv       the student table as a spreadsheet file

timeline_for and summary_for are the two functions every page shares, so the numbers on
the student page, the supervisor page, the cohort page and the spreadsheet always agree.
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


def days_text(n):
    """1 day, 2 days: the number with the right word after it."""
    return f"{n} day{'' if n == 1 else 's'}"


def timeline_for(student, now=None):
    """Goes through every deliverable and works out where this student stands on each one."""
    now = now or timezone.now()
    submissions = {s.deliverable_id: s for s in Submission.objects.filter(student=student).defer("data").order_by("submitted_at")}
    rows = []
    for d in Deliverable.objects.all():
        sub = submissions.get(d.id)
        days_left = (d.due_at - now).days
        if sub:
            late = sub.days_late()
            status, label = ("late", f"Submitted {days_text(late)} late") if late else ("done", "Submitted")
        elif d.due_at < now:
            status, label = "missing", "Missing"
        else:
            status = "soon" if days_left <= 7 else "upcoming"
            label = "Due today" if days_left == 0 else f"Due in {days_text(days_left)}"
        rows.append({"deliverable": d, "submission": sub, "status": status, "label": label})
    return rows


def progress_for(rows):
    """How far through the deliverables a student is: how many are handed in, out of how many, as a percent."""
    total = len(rows)
    done = sum(1 for r in rows if r["status"] in ("done", "late"))
    return {"done": done, "total": total, "percent": round(100 * done / total) if total else 0}


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
        "progress": progress_for(rows),
        "feedback": request.user.feedback_received.select_related("supervisor")[:5],
        "emails": NotificationLog.objects.filter(recipient=request.user).order_by("-sent_at")[:5],
        "submitted_count": sum(1 for r in rows if r["status"] in ("done", "late")),
        "missing_count": sum(1 for r in rows if r["status"] == "missing"),
    })


def summary_for(student, now, due_count):
    """One line about a student: their score, how much is in, how much is missing, last meeting."""
    rows = timeline_for(student, now)
    latest = RiskScore.objects.filter(student=student).first()
    week_ago = RiskScore.objects.filter(student=student, scored_on__lte=timezone.localdate(now) - timedelta(days=7)).first()
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
        "last_meeting": Meeting.counted().filter(student=student).order_by("-held_on").first(),
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
        "to_confirm": Meeting.objects.filter(student__supervisor=request.user, status=Meeting.Status.WAITING).count(),
        "activity": recent_activity(request.user, now),
        "emails": NotificationLog.objects.filter(recipient=request.user).order_by("-sent_at")[:8],
    })


def recent_activity(supervisor, now, days=7):
    """What this supervisor's students did in the last week: uploads and meetings, newest first."""
    since = now - timedelta(days=days)
    items = []
    for sub in Submission.objects.filter(student__supervisor=supervisor, submitted_at__gte=since).defer("data").select_related("student", "deliverable"):
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
            overdue = "it was due today" if days == 0 else f"it is {days_text(days)} overdue"
            steps.append((0, f"Upload {r['deliverable'].title}, {overdue}", r["deliverable"]))
    for m in Meeting.objects.filter(student=student, status=Meeting.Status.REJECTED):
        steps.append((0, f"Your supervisor marked the meeting of {m.held_on:%-d %B} as not held, record the real one", None))
    last = Meeting.counted().filter(student=student).order_by("-held_on").first()
    gap = (timezone.localdate(now) - last.held_on).days if last else None
    if last is None:
        steps.append((1, "Record your first meeting with your supervisor", None))
    elif gap > 7:
        steps.append((1, f"Record your latest meeting, the last one recorded was {gap} days ago", None))
    open_actions = Action.objects.filter(meeting__student=student, done=False).exclude(meeting__status=Meeting.Status.REJECTED).count()
    if open_actions:
        steps.append((2, f"{open_actions} agreed action{'s are' if open_actions != 1 else ' is'} still open, tick them off when done", None))
    for r in rows:
        if r["status"] == "soon":
            left = (r["deliverable"].due_at - now).days
            when = "today" if left == 0 else f"in {days_text(left)}"
            steps.append((3, f"{r['deliverable'].title} is due {when} and nothing is uploaded yet", r["deliverable"]))
            break
    return [{"text": t, "deliverable": d} for _, t, d in sorted(steps, key=lambda x: x[0])]


# plain words for each indicator, used when we say why a student is amber or red
INDICATOR_WORDS = {
    "overdue": "work overdue",
    "lateness": "work handed in late",
    "supervision": "no recent meeting",
    "proximity": "deadline close, nothing uploaded",
    "actions": "agreed actions still open",
}


# a student red for this many days in a row is flagged to the coordinator, the supervisor alone has not moved them
STUCK_DAYS = 14


def red_days(student, today):
    """How many days the student has been red without a break, counted back from their latest score."""
    start = None
    for scored_on, status in student.risk_scores.order_by("-scored_on").values_list("scored_on", "status"):
        if status != "red":
            break
        start = scored_on
    return (today - start).days + 1 if start else 0


def main_reason(risk):
    """The indicator that added the most points to a score, in plain words."""
    if not risk or not risk.breakdown:
        return ""
    name, part = max(risk.breakdown.items(), key=lambda item: item[1]["points"])
    return INDICATOR_WORDS.get(name, name) if part["points"] > 0 else ""


def deliverable_stats(students, now):
    """For every deliverable: how many students handed it in, how many were late, how many are missing."""
    total = len(students)
    rows = []
    for d in Deliverable.objects.all():
        # one student counts once, even if an old record holds two files for the same deliverable
        first = {}
        for sub in Submission.objects.filter(deliverable=d, student__in=students).defer("data").order_by("submitted_at"):
            first.setdefault(sub.student_id, sub)
        submitted = len(first)
        due = d.due_at < now
        rows.append({
            "deliverable": d, "due": due, "submitted": submitted,
            "late": sum(1 for sub in first.values() if sub.days_late() > 0),
            "missing": total - submitted if due else 0,
            "percent": round(100 * submitted / total) if total else 0,
            "days_left": (d.due_at - now).days,
        })
    return rows


def meeting_stats(summaries, today):
    """How recently each student met their supervisor, counted into four groups."""
    groups = {"week": 0, "fortnight": 0, "older": 0, "never": 0}
    for s in summaries:
        last = s["last_meeting"]
        if last is None:
            groups["never"] += 1
            continue
        gap = (today - last.held_on).days
        groups["week" if gap <= 7 else "fortnight" if gap <= 14 else "older"] += 1
    return groups


def colour_history():
    """How many students were green, amber and red on each day that was scored, for the chart."""
    from django.db.models import Count
    days = {}
    for row in RiskScore.objects.values("scored_on", "status").annotate(n=Count("id")).order_by("scored_on"):
        days.setdefault(row["scored_on"], {"green": 0, "amber": 0, "red": 0})[row["status"]] = row["n"]
    return {
        "labels": [day.strftime("%d %b") for day in days],
        "green": [c["green"] for c in days.values()],
        "amber": [c["amber"] for c in days.values()],
        "red": [c["red"] for c in days.values()],
    }


@role_required("coordinator")
def coordinator_home(request):
    """The coordinator's view of the whole cohort.

    The top half is statistics: the colours today and over time, who needs attention and why, how each
    deliverable went, how recently students met their supervisors, and one line per supervisor.
    The bottom half lists every student under their supervisor. Students with no supervisor yet get
    their own group at the end, so nobody is lost.
    """
    from accounts.models import User
    now = timezone.now()
    due_count = Deliverable.objects.filter(due_at__lt=now).count()
    totals = {"green": 0, "amber": 0, "red": 0, "none": 0, "students": 0, "missing": 0, "waiting": 0}
    groups, everyone = [], []

    def group_for(name, students):
        counts = {"green": 0, "amber": 0, "red": 0, "none": 0}
        rows = [summary_for(student, now, due_count) for student in students]
        for row in rows:
            row["supervisor_name"] = name
            status = row["risk"].status if row["risk"] else "none"
            counts[status] += 1
            totals[status] += 1
        scores = [row["risk"].score for row in rows if row["risk"]]
        missing = sum(row["missing"] for row in rows)
        totals["students"] += len(rows)
        totals["missing"] += missing
        everyone.extend(rows)
        waiting = Meeting.objects.filter(student__in=[row["user"] for row in rows], status=Meeting.Status.WAITING).count()
        totals["waiting"] += waiting
        return {
            "name": name, "rows": rows, "counts": counts, "total": len(rows), "missing": missing, "waiting": waiting,
            "average": round(sum(scores) / len(scores)) if scores else None,
            "no_meeting": sum(1 for row in rows if row["last_meeting"] is None
                              or (timezone.localdate(now) - row["last_meeting"].held_on).days > 14),
        }

    supervisors = list(User.objects.filter(role="supervisor").order_by("last_name", "first_name"))
    for supervisor in supervisors:
        groups.append(group_for(supervisor.get_full_name() or supervisor.username,
                                supervisor.students.order_by("last_name", "first_name")))
    unassigned = User.objects.filter(role="student", supervisor__isnull=True).order_by("last_name", "first_name")
    if unassigned.exists():
        groups.append(group_for("No supervisor yet", unassigned))
    totals["supervisors"] = len(supervisors)

    # amber and red students, worst first, each with the main reason for their score
    today = timezone.localdate(now)
    attention = [row for row in everyone if row["risk"] and row["risk"].status != "green"]
    for row in attention:
        row["reason"] = main_reason(row["risk"])
        row["red_days"] = red_days(row["user"], today) if row["risk"].status == "red" else 0
        row["stuck"] = row["red_days"] >= STUCK_DAYS
    # the students stuck in red come first, then the rest worst score first
    attention.sort(key=lambda row: (not row["stuck"], -row["risk"].score))
    totals["stuck"] = sum(1 for row in attention if row["stuck"])

    return render(request, "dashboard/coordinator_home.html", {
        "groups": groups, "totals": totals, "attention": attention,
        "deliverables": deliverable_stats([row["user"] for row in everyone], now),
        "meetings": meeting_stats(everyone, timezone.localdate(now)),
        "history": colour_history(),
    })


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
