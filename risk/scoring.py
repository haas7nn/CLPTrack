"""The risk score, which is the heart of the whole system.

We look at five signs of how a student is doing. Each sign becomes a number
from 0 (all fine) to 1 (as bad as it gets), we multiply it by its weight, and
add the five up to get a score out of 100.

    below 30   green
    30 to 59   amber
    60 and up  red

The weights, the cut off points and the semester start date can be changed in
settings.py without touching this file.
"""
from datetime import date

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
    """Makes sure a number stays between 0 and 1."""
    return max(0.0, min(1.0, value))


def overdue_indicator(student, now):
    """Of the things already due, what share has nothing handed in."""
    due = Deliverable.objects.filter(due_at__lt=now)
    total = due.count()
    if total == 0:
        return 0.0
    submitted = Submission.objects.filter(student=student, deliverable__in=due).values("deliverable").distinct().count()
    return clamp((total - submitted) / total)


def lateness_indicator(student):
    """On average, how many days late is this student, out of the 7 day cap."""
    submissions = list(Submission.objects.filter(student=student).select_related("deliverable"))
    if not submissions:
        return 0.0
    average = sum(s.days_late() for s in submissions) / len(submissions)
    return clamp(average / LATENESS_CAP_DAYS)


def supervision_indicator(student, today):
    """How long since the last meeting, beyond the one week that is allowed."""
    last = Meeting.objects.filter(student=student).order_by("-held_on").first()
    since = last.held_on if last else semester_start()
    gap = (today - since).days
    return clamp((gap - MEETING_RULE_DAYS) / SUPERVISION_CAP_DAYS)


def proximity_indicator(student, now):
    """Is the next deadline close, with nothing uploaded for it yet."""
    upcoming = Deliverable.objects.filter(due_at__gte=now).order_by("due_at").first()
    if upcoming is None:
        return 0.0
    if Submission.objects.filter(student=student, deliverable=upcoming).exists():
        return 0.0
    days_left = (upcoming.due_at - now).total_seconds() / 86400  # fractional days, so a deadline in 2.5 days counts as 2.5
    if days_left >= PROXIMITY_WINDOW_DAYS:
        return 0.0
    return clamp((PROXIMITY_WINDOW_DAYS - days_left) / PROXIMITY_WINDOW_DAYS)


def actions_indicator(student):
    """What share of the things agreed in meetings are still not done."""
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
    """Works out the score for one student and says what each sign contributed."""
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
