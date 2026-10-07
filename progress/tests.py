"""Tests for uploading, meetings, feedback and the daily scoring."""
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from progress.models import Action, Deliverable, Meeting, Submission
from risk.models import RiskScore


class ProgressTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        self.student = User.objects.create_user("stu", role="student", password="x", supervisor=self.supervisor,
                                                first_name="Zahra", last_name="Mahmood")
        self.deliverable = Deliverable.objects.create(title="Reflection 1", order=1, due_at=timezone.now())
        self.client.login(username="stu", password="x")

    def test_student_can_upload_a_pdf(self):
        pdf = SimpleUploadedFile("reflection.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.client.post(reverse("submit", args=[self.deliverable.id]), {"file": pdf, "note": "first draft"})
        self.assertRedirects(response, reverse("student_home"))
        self.assertEqual(Submission.objects.filter(student=self.student).count(), 1)

    def test_wrong_file_type_is_refused(self):
        bad = SimpleUploadedFile("virus.exe", b"nope", content_type="application/octet-stream")
        response = self.client.post(reverse("submit", args=[self.deliverable.id]), {"file": bad})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please upload a PDF")
        self.assertEqual(Submission.objects.count(), 0)

    def test_recording_a_meeting_creates_its_actions(self):
        response = self.client.post(reverse("meetings"), {
            "held_on": "2026-10-08", "discussed": "Proposal approved", "actions": "Send final proposal\nStart the design\n"})
        self.assertRedirects(response, reverse("meetings"))
        meeting = Meeting.objects.get(student=self.student)
        self.assertEqual(meeting.actions.count(), 2)

    def test_student_cannot_tick_another_students_action(self):
        other = User.objects.create_user("other", role="student", password="x")
        meeting = Meeting.objects.create(student=other, held_on="2026-10-01", discussed="x")
        action = Action.objects.create(meeting=meeting, description="theirs")
        response = self.client.post(reverse("action_done", args=[action.id]))
        self.assertEqual(response.status_code, 404)
        action.refresh_from_db()
        self.assertFalse(action.done)

    def test_supervisor_can_open_own_student_and_leave_feedback(self):
        self.client.login(username="sup", password="x")
        response = self.client.post(reverse("student_detail", args=[self.student.id]), {"text": "Good start"})
        self.assertRedirects(response, reverse("student_detail", args=[self.student.id]))
        self.assertEqual(self.student.feedback_received.count(), 1)

    def test_supervisor_cannot_open_someone_elses_student(self):
        other_sup = User.objects.create_user("sup2", role="supervisor", password="x")
        self.client.login(username="sup2", password="x")
        response = self.client.get(reverse("student_detail", args=[self.student.id]))
        self.assertEqual(response.status_code, 404)

    def test_daily_scoring_saves_one_row_per_student(self):
        call_command("score_students", verbosity=0)
        call_command("score_students", verbosity=0)  # a second run the same day must not add a second row
        self.assertEqual(RiskScore.objects.filter(student=self.student).count(), 1)
        row = RiskScore.objects.get(student=self.student)
        self.assertIn(row.status, ["green", "amber", "red"])
        self.assertIn("overdue", row.breakdown)


class DownloadTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        self.other = User.objects.create_user("sup2", role="supervisor", password="x")
        self.student = User.objects.create_user("stu", role="student", password="x", supervisor=self.supervisor)
        self.deliverable = Deliverable.objects.create(title="Thesis", order=8, due_at=timezone.now() + timedelta(days=5))
        self.submission = Submission.objects.create(student=self.student, deliverable=self.deliverable,
                                                    filename="thesis.pdf", content_type="application/pdf",
                                                    size=9, data=b"%PDF-1.4 x")

    def test_student_and_own_supervisor_can_download(self):
        for name in ("stu", "sup"):
            self.client.login(username=name, password="x")
            response = self.client.get(reverse("download", args=[self.submission.id]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"%PDF-1.4 x")
            self.assertIn("thesis.pdf", response["Content-Disposition"])

    def test_other_supervisor_cannot_download(self):
        self.client.login(username="sup2", password="x")
        self.assertEqual(self.client.get(reverse("download", args=[self.submission.id])).status_code, 403)

    def test_file_bytes_are_kept_in_the_database(self):
        self.client.login(username="stu", password="x")
        pdf = SimpleUploadedFile("draft.pdf", b"%PDF-1.4 draft", content_type="application/pdf")
        self.client.post(reverse("submit", args=[self.deliverable.id]), {"file": pdf})
        saved = Submission.objects.get(filename="draft.pdf")
        self.assertEqual(bytes(saved.data), b"%PDF-1.4 draft")
        self.assertEqual(saved.size, len(b"%PDF-1.4 draft"))
