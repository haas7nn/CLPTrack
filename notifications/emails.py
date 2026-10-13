"""The two kinds of email the system sends.

Reminders   to a student, a few days before a deadline they have not submitted for
Alerts      to a supervisor, when one of their students changes colour
Each email is written to the NotificationLog, and the reference field makes sure
the same reminder or alert is never sent twice.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import User
from progress.models import Deliverable, Submission
from risk.models import RiskScore
from .models import NotificationLog

logger = logging.getLogger(__name__)
REMIND_DAYS_BEFORE = (3, 1)  # a reminder three days before and one day before


def _send(kind, user, subject, body, reference):
    """Send one email unless it was already sent, and log it."""
    if not user.email or NotificationLog.objects.filter(recipient=user, reference=reference).exists():
        return False
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception as error:
        # one address the mail service refuses must not stop everybody else's email
        logger.warning("email to %s was not sent: %s", user.username, error)
        return False
    NotificationLog.objects.create(kind=kind, recipient=user, subject=subject, reference=reference)
    return True


def send_deadline_reminders(now=None):
    """Remind every student about each deadline that is about 3 days or 1 day away with nothing uploaded.

    The three day reminder goes out when the deadline is between 2 and 4 days away, the one day reminder
    when it is less than 2 days away. The wide windows mean a reminder is still sent, a day late, if the
    job missed a day. The reference stops either one going twice.
    """
    now = now or timezone.now()
    sent = 0
    windows = {3: (timedelta(days=2), timedelta(days=4)), 1: (timedelta(0), timedelta(days=2))}
    for days in REMIND_DAYS_BEFORE:
        window_start, window_end = now + windows[days][0], now + windows[days][1]
        for deliverable in Deliverable.objects.filter(due_at__gt=window_start, due_at__lte=window_end):
            left = (deliverable.due_at - now).days
            when = "today" if left == 0 else f"in {left} day{'s' if left != 1 else ''}"
            for student in User.objects.filter(role=User.Role.STUDENT):
                if Submission.objects.filter(student=student, deliverable=deliverable).exists():
                    continue
                subject = f"CLPTrack reminder: {deliverable.title} is due {when}"
                body = (f"Hi {student.first_name or student.username},\n\n"
                        f"{deliverable.title} is due on {timezone.localtime(deliverable.due_at):%A %d %B at %H:%M} "
                        f"and you have not uploaded anything for it yet.\n\nCLPTrack")
                sent += _send(NotificationLog.Kind.REMINDER, student, subject, body,
                              reference=f"reminder:{deliverable.id}:{days}")
    return sent


def send_status_alerts(today=None):
    """Tell a supervisor when one of their students changed colour since yesterday."""
    today = today or timezone.localdate()
    sent = 0
    for score in RiskScore.objects.filter(scored_on=today).select_related("student", "student__supervisor"):
        supervisor = score.student.supervisor
        if supervisor is None:
            continue
        previous = RiskScore.objects.filter(student=score.student, scored_on__lt=today).order_by("-scored_on").first()
        if previous and previous.status == score.status:
            continue
        if previous is None and score.status == RiskScore.Status.GREEN:
            continue  # a new student who is fine does not need an alert
        name = score.student.get_full_name() or score.student.username
        was = previous.get_status_display() if previous else "not scored"
        subject = f"CLPTrack alert: {name} is now {score.get_status_display()}"
        body = (f"Hi {supervisor.first_name or supervisor.username},\n\n"
                f"{name} changed from {was} to {score.get_status_display()} today, with a score of {score.score}.\n"
                f"Indicators: " + ", ".join(f"{k} {v['points']}" for k, v in score.breakdown.items()) +
                "\n\nCLPTrack")
        sent += _send(NotificationLog.Kind.ALERT, supervisor, subject, body,
                      reference=f"alert:{score.student_id}:{today}:{score.status}")
    return sent
