"""The risk score.

Five indicators describe how a student is doing. Each one is turned into a
value between 0 (no concern) and 1 (worst case), multiplied by its weight, and
the five results are added to give a score from 0 to 100.

    below 30   green
    30 to 59   amber
    60 and up  red

The weights, the thresholds and the semester start date live in settings, so
they can be changed without touching this file.
"""
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from progress.models import Action, Deliverable, Submission, Meeting

DEFAULT_WEIGHTS = {
    "overdue": 35,      # share of due deliverables with no submission
    "lateness": 20,     # average delay of submitted work, capped at 7 days
    "supervision": 25,  # days since the last meeting beyond the weekly rule, capped at 14
    "proximity": 10,    # a deadline within 7 days with nothing uploaded
    "actions": 10,      # share of agreed actions still open
}
LATENESS_CAP_DAYS = 7
MEETING_RULE_DAYS = 7
SUPERVISION_CAP_DAYS = 14
PROXIMITY_WINDOW_DAYS = 7


def weights():
    return getattr(settings, "RISK_WEIGHTS", DEFAULT_WEIGHTS)


def thresholds():
    return getattr(settings, "RISK_AMBER_FROM", 30), getattr(settings, "RISK_RED_FROM", 60)


def semester_start():
    return getattr(settings, "SEMESTER_START", date(2026, 9, 13))


def clamp(value):
    """Keep a value between 0 and 1."""
    return max(0.0, min(1.0, value))


def overdue_indicator(student, now):
    """Share of the deliverables already due that have no submission."""
    due = Deliverable.objects.filter(due_at__lt=now)
    total = due.count()
    if total == 0:
        return 0.0
    submitted = Submission.objects.filter(student=student, deliverable__in=due).values("deliverable").distinct().count()
    return clamp((total - submitted) / total)


def lateness_indicator(student):
    """Average number of days late across the student's submissions, out of the cap."""
    submissions = list(Submission.objects.filter(student=student).select_related("deliverable"))
    if not submissions:
        return 0.0
    average = sum(s.days_late() for s in submissions) / len(submissions)
    return clamp(average / LATENESS_CAP_DAYS)


def supervision_indicator(student, today):
    """How far the gap since the last meeting runs beyond the weekly rule."""
    last = Meeting.objects.filter(student=student).order_by("-held_on").first()
    since = last.held_on if last else semester_start()
    gap = (today - since).days
    return clamp((gap - MEETING_RULE_DAYS) / SUPERVISION_CAP_DAYS)


def proximity_indicator(student, now):
    """How close the next deadline is when nothing has been uploaded for it."""
    upcoming = Deliverable.objects.filter(due_at__gte=now).order_by("due_at").first()
    if upcoming is None:
        return 0.0
    if Submission.objects.filter(student=student, deliverable=upcoming).exists():
        return 0.0
    days_left = (upcoming.due_at - now).days
    if days_left >= PROXIMITY_WINDOW_DAYS:
        return 0.0
    return clamp((PROXIMITY_WINDOW_DAYS - days_left) / PROXIMITY_WINDOW_DAYS)


def actions_indicator(student):
    """Share of the actions agreed in meetings that are still open."""
    actions = Action.objects.filter(meeting__student=student)
    total = actions.count()
    if total == 0:
        return 0.0
    return clamp(actions.filter(done=False).count() / total)


def status_for(score):
    amber_from, red_from = thresholds()
    if score >= red_from:
        return "red"
    if score >= amber_from:
        return "amber"
    return "green"


def compute(student, now=None):
    """Work out the score for one student. Returns the score, the status and the breakdown."""
    now = now or timezone.now()
    today = now.date()
    values = {
        "overdue": overdue_indicator(student, now),
        "lateness": lateness_indicator(student),
        "supervision": supervision_indicator(student, today),
        "proximity": proximity_indicator(student, now),
        "actions": actions_indicator(student),
    }
    w = weights()
    breakdown = {name: {"value": round(value, 2), "weight": w[name], "points": round(value * w[name], 1)}
                 for name, value in values.items()}
    score = round(sum(part["points"] for part in breakdown.values()))
    return {"score": score, "status": status_for(score), "breakdown": breakdown}
