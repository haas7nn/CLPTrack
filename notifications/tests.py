"""Tests for the emails: the right people get them, and never twice."""
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from notifications import emails
from notifications.models import NotificationLog
from progress.models import Deliverable
from risk.models import RiskScore


class EmailTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x", email="sup@example.com")
        self.student = User.objects.create_user("stu", role="student", password="x", email="stu@example.com",
                                                supervisor=self.supervisor, first_name="Zahra")

    def test_reminder_goes_out_three_days_before_and_only_once(self):
        now = timezone.now()
        Deliverable.objects.create(title="Reflection 2", order=3, due_at=now + timedelta(days=3, hours=2))
        self.assertEqual(emails.send_deadline_reminders(now), 1)
        self.assertEqual(emails.send_deadline_reminders(now), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reflection 2", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["stu@example.com"])
        self.assertEqual(NotificationLog.objects.count(), 1)

    def test_no_reminder_when_the_deadline_is_far_away(self):
        Deliverable.objects.create(title="Thesis", order=8, due_at=timezone.now() + timedelta(days=40))
        self.assertEqual(emails.send_deadline_reminders(), 0)

    def test_supervisor_is_alerted_when_a_student_turns_red(self):
        today = timezone.localdate()
        RiskScore.objects.create(student=self.student, scored_on=today - timedelta(days=1), score=10, status="green")
        RiskScore.objects.create(student=self.student, scored_on=today, score=65, status="red",
                                 breakdown={"overdue": {"points": 35}})
        self.assertEqual(emails.send_status_alerts(today), 1)
        self.assertEqual(mail.outbox[0].to, ["sup@example.com"])
        self.assertIn("Zahra", mail.outbox[0].subject)
        self.assertEqual(emails.send_status_alerts(today), 0)  # not twice

    def test_no_alert_when_the_colour_did_not_change(self):
        today = timezone.localdate()
        RiskScore.objects.create(student=self.student, scored_on=today - timedelta(days=1), score=40, status="amber")
        RiskScore.objects.create(student=self.student, scored_on=today, score=45, status="amber")
        self.assertEqual(emails.send_status_alerts(today), 0)


class BrevoBackendTests(TestCase):
    def test_one_request_per_message_with_sender_and_recipient(self):
        from unittest import mock
        from django.core.mail import EmailMessage
        from notifications.brevo import BrevoEmailBackend
        calls = []

        class FakeResponse:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_urlopen(request, timeout=0):
            calls.append((request.full_url, request.get_header("Api-key"), json.loads(request.data)))
            return FakeResponse()

        import json
        with self.settings(BREVO_API_KEY="key-for-test", DEFAULT_FROM_EMAIL="CLPTrack <from@example.com>"):
            with mock.patch("urllib.request.urlopen", fake_urlopen):
                n = BrevoEmailBackend().send_messages([EmailMessage("Hello", "Body", "CLPTrack <from@example.com>", ["to@example.com"])])
        self.assertEqual(n, 1)
        url, key, payload = calls[0]
        self.assertIn("api.brevo.com", url)
        self.assertEqual(key, "key-for-test")
        self.assertEqual(payload["sender"], {"email": "from@example.com", "name": "CLPTrack"})
        self.assertEqual(payload["to"], [{"email": "to@example.com"}])
        self.assertEqual(payload["subject"], "Hello")


class OneBadAddressTests(TestCase):
    """An email the mail service refuses must not stop everybody else's."""

    def test_the_other_students_still_get_their_reminder(self):
        from datetime import timedelta
        from unittest import mock
        from django.core import mail
        from django.utils import timezone
        from accounts.models import User
        from notifications import emails
        from notifications.models import NotificationLog
        from progress.models import Deliverable
        now = timezone.now()
        Deliverable.objects.create(title="Reflection 2", order=1, due_at=now + timedelta(days=3, hours=1))
        for name in ("first", "broken", "last"):
            User.objects.create_user(name, role="student", password="x", email=f"{name}@example.com")
        real_send = emails.send_mail

        def refuse_one(subject, body, sender, to):
            if to == ["broken@example.com"]:
                raise OSError("the mail service refused this address")
            return real_send(subject, body, sender, to)

        with mock.patch.object(emails, "send_mail", side_effect=refuse_one):
            sent = emails.send_deadline_reminders(now)
        self.assertEqual(sent, 2)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["first@example.com", "last@example.com"])
        self.assertFalse(NotificationLog.objects.filter(recipient__username="broken").exists())   # so it is tried again tomorrow


class ReminderWindowTests(TestCase):
    def test_a_reminder_still_goes_out_if_the_job_missed_a_day(self):
        from datetime import timedelta
        from django.core import mail
        from django.utils import timezone
        from accounts.models import User
        from notifications import emails
        from progress.models import Deliverable
        now = timezone.now()
        Deliverable.objects.create(title="Reflection 3", order=1, due_at=now + timedelta(days=2, hours=5))
        User.objects.create_user("stu", role="student", password="x", email="stu@example.com")
        self.assertEqual(emails.send_deadline_reminders(now), 1)      # the three day reminder, a day late
        self.assertIn("is due in 2 days", mail.outbox[0].subject)
        self.assertEqual(emails.send_deadline_reminders(now), 0)      # and never twice
        self.assertEqual(emails.send_deadline_reminders(now + timedelta(days=1, hours=6)), 1)   # then the one day reminder
        self.assertIn("is due today", mail.outbox[1].subject)
