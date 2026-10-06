"""Tests for the risk score, including the worked example from the project plan."""
from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from progress.models import Action, Deliverable, Meeting, Submission
from risk import scoring


def at(days_from_now, hour=12):
    now = timezone.now()
    base = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    return base + timedelta(days=days_from_now)


class RiskScoreTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("student1", role="student", password="x")

    def test_new_student_with_nothing_due_is_green_apart_from_meetings(self):
        result = scoring.compute(self.student)
        self.assertEqual(result["breakdown"]["overdue"]["points"], 0)
        self.assertEqual(result["breakdown"]["actions"]["points"], 0)
        self.assertIn(result["status"], ["green", "amber", "red"])

    def test_worked_example_from_the_plan_scores_amber(self):
        now = timezone.now()
        # four deliverables already due, one of them never submitted
        due = [Deliverable.objects.create(title=f"D{i}", order=i, due_at=at(-20 + i * 2)) for i in range(4)]
        for d in due[:3]:
            Submission.objects.create(student=self.student, deliverable=d,
                                      file=ContentFile(b"x", name="a.pdf"),
                                      submitted_at=d.due_at + timedelta(days=3))  # three days late each
        # last meeting 16 days ago, with four actions, two still open
        meeting = Meeting.objects.create(student=self.student, held_on=(now - timedelta(days=16)).date(), discussed="plan")
        for i in range(4):
            Action.objects.create(meeting=meeting, description=f"task {i}", done=(i < 2))
        # next deadline in three days with nothing uploaded
        Deliverable.objects.create(title="Next", order=9, due_at=at(3))

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
