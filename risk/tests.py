"""Tests for the risk score, including the worked example from the project plan."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from progress.models import Action, Deliverable, Meeting, Submission
from risk import scoring


class RiskScoreTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("student1", role="student", password="x")

    def test_new_student_with_nothing_due_is_green_apart_from_meetings(self):
        result = scoring.compute(self.student)
        self.assertEqual(result["breakdown"]["overdue"]["points"], 0)
        self.assertEqual(result["breakdown"]["actions"]["points"], 0)
        self.assertIn(result["status"], ["green", "amber", "red"])

    def test_worked_example_from_the_plan_scores_amber(self):
        now = timezone.now().replace(microsecond=0)
        day = timedelta(days=1)
        # four deliverables already due, one of them never submitted
        due = [Deliverable.objects.create(title=f"D{i}", order=i, due_at=now - (20 - 2 * i) * day) for i in range(4)]
        for d in due[:3]:
            Submission.objects.create(student=self.student, deliverable=d,
                                      filename="a.pdf", data=b"x",
                                      submitted_at=d.due_at + 3 * day)  # three days late each
        # last meeting 16 days ago, with four actions, two still open
        meeting = Meeting.objects.create(student=self.student, held_on=(now - 16 * day).date(), discussed="plan")
        for i in range(4):
            Action.objects.create(meeting=meeting, description=f"task {i}", done=(i < 2))
        # next deadline in exactly three days with nothing uploaded
        Deliverable.objects.create(title="Next", order=9, due_at=now + 3 * day)

        result = scoring.compute(self.student, now=now)
        b = result["breakdown"]
        self.assertAlmostEqual(b["overdue"]["value"], 0.25)
        self.assertAlmostEqual(b["lateness"]["value"], 0.43, places=2)
        self.assertAlmostEqual(b["supervision"]["value"], 0.64, places=2)
        self.assertAlmostEqual(b["proximity"]["value"], 0.57, places=2)
        self.assertAlmostEqual(b["actions"]["value"], 0.5)
        self.assertEqual(result["score"], 44)
        self.assertEqual(result["status"], "amber")

    def test_thresholds(self):
        self.assertEqual(scoring.status_for(0), "green")
        self.assertEqual(scoring.status_for(29), "green")
        self.assertEqual(scoring.status_for(30), "amber")
        self.assertEqual(scoring.status_for(59), "amber")
        self.assertEqual(scoring.status_for(60), "red")
        self.assertEqual(scoring.status_for(100), "red")

    def test_weights_add_up_to_one_hundred(self):
        self.assertEqual(sum(scoring.weights().values()), 100)


class DailyTaskUrlTests(TestCase):
    """The daily address only works with the secret token."""

    def test_wrong_or_missing_token_is_refused(self):
        with self.settings(DAILY_TASK_TOKEN="secret"):
            self.assertEqual(self.client.post("/tasks/daily/").status_code, 403)
            self.assertEqual(self.client.post("/tasks/daily/", HTTP_X_TASK_TOKEN="nope").status_code, 403)

    def test_no_token_configured_means_switched_off(self):
        with self.settings(DAILY_TASK_TOKEN=""):
            self.assertEqual(self.client.post("/tasks/daily/", HTTP_X_TASK_TOKEN="").status_code, 403)

    def test_right_token_runs_the_job(self):
        with self.settings(DAILY_TASK_TOKEN="secret"):
            response = self.client.post("/tasks/daily/", HTTP_X_TASK_TOKEN="secret")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/tasks/daily/").status_code, 405)


class TestEmailUrlTests(TestCase):
    def test_sends_one_email_with_the_token_and_refuses_without(self):
        from django.core import mail
        with self.settings(DAILY_TASK_TOKEN="secret"):
            self.assertEqual(self.client.post("/tasks/test-email/", {"to": "me@example.com"}).status_code, 403)
            response = self.client.post("/tasks/test-email/", {"to": "me@example.com"}, HTTP_X_TASK_TOKEN="secret")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["me@example.com"])
