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

    def test_uploading_again_replaces_the_file_and_keeps_the_first_time(self):
        first = SimpleUploadedFile("v1.pdf", b"%PDF-1.4 one", content_type="application/pdf")
        self.client.post(reverse("submit", args=[self.deliverable.id]), {"file": first})
        original = Submission.objects.get(student=self.student)
        Submission.objects.filter(pk=original.pk).update(submitted_at=timezone.now() - timedelta(days=3))
        second = SimpleUploadedFile("v2.pdf", b"%PDF-1.4 two", content_type="application/pdf")
        response = self.client.post(reverse("submit", args=[self.deliverable.id]), {"file": second, "note": "fixed"})
        self.assertRedirects(response, reverse("student_home"))
        self.assertEqual(Submission.objects.filter(student=self.student).count(), 1)
        replaced = Submission.objects.get(pk=original.pk)
        self.assertEqual(replaced.filename, "v2.pdf")
        self.assertEqual(bytes(replaced.data), b"%PDF-1.4 two")
        self.assertLess(replaced.submitted_at, timezone.now() - timedelta(days=2))

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

    def test_a_meeting_cannot_be_recorded_for_a_future_date(self):
        future = (timezone.localdate() + timedelta(days=30)).isoformat()
        response = self.client.post(reverse("meetings"), {"held_on": future, "discussed": "Not yet", "actions": ""})
        self.assertContains(response, "this meeting has not happened yet")
        self.assertEqual(Meeting.objects.count(), 0)

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
        User.objects.create_user("sup2", role="supervisor", password="x")
        self.client.login(username="sup2", password="x")
        response = self.client.get(reverse("student_detail", args=[self.student.id]))
        self.assertEqual(response.status_code, 404)

    def test_student_sees_the_feedback_on_their_timeline(self):
        self.client.login(username="sup", password="x")
        self.client.post(reverse("student_detail", args=[self.student.id]), {"text": "Tighten the aims"})
        self.client.login(username="stu", password="x")
        response = self.client.get(reverse("student_home"))
        self.assertContains(response, "Tighten the aims")

    def test_supervisor_sees_the_note_sent_with_an_upload(self):
        pdf = SimpleUploadedFile("reflection.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.client.post(reverse("submit", args=[self.deliverable.id]), {"file": pdf, "note": "second attempt after your comments"})
        self.client.login(username="sup", password="x")
        response = self.client.get(reverse("student_detail", args=[self.student.id]))
        self.assertContains(response, "second attempt after your comments")
        self.assertContains(response, "reflection.pdf")

    def test_coordinator_can_read_any_student_but_not_write_feedback(self):
        User.objects.create_user("coord", role="coordinator", password="x")
        self.client.login(username="coord", password="x")
        response = self.client.get(reverse("student_detail", args=[self.student.id]))
        self.assertContains(response, "Zahra Mahmood")
        self.assertNotContains(response, "Leave feedback")
        response = self.client.post(reverse("student_detail", args=[self.student.id]), {"text": "nope"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.student.feedback_received.count(), 0)

    def test_student_cannot_open_the_detail_page(self):
        response = self.client.get(reverse("student_detail", args=[self.student.id]))
        self.assertEqual(response.status_code, 403)

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


class MeetingConfirmationTests(TestCase):
    """The student records a meeting, the supervisor says if it happened."""

    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        self.student = User.objects.create_user("stu", role="student", password="x", supervisor=self.supervisor,
                                                first_name="Zahra", last_name="Mahmood")
        self.today = timezone.localdate()
        self.meeting = Meeting.objects.create(student=self.student, held_on=self.today, discussed="Scope")

    def test_a_new_meeting_waits_for_confirmation(self):
        self.assertEqual(self.meeting.status, "waiting")
        self.client.login(username="stu", password="x")
        self.assertContains(self.client.get(reverse("meetings")), "Waiting for confirmation")

    def test_supervisor_confirms_a_meeting(self):
        self.client.login(username="sup", password="x")
        response = self.client.post(reverse("meeting_review", args=[self.meeting.id]), {"decision": "confirmed"})
        self.assertRedirects(response, reverse("student_detail", args=[self.student.id]))
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "confirmed")
        self.assertIsNotNone(self.meeting.reviewed_at)

    def test_only_the_students_own_supervisor_can_review(self):
        User.objects.create_user("sup2", role="supervisor", password="x")
        self.client.login(username="sup2", password="x")
        response = self.client.post(reverse("meeting_review", args=[self.meeting.id]), {"decision": "rejected"})
        self.assertEqual(response.status_code, 404)
        self.client.login(username="stu", password="x")   # a student cannot confirm their own meeting
        response = self.client.post(reverse("meeting_review", args=[self.meeting.id]), {"decision": "confirmed"})
        self.assertEqual(response.status_code, 403)
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "waiting")

    def test_a_rejected_meeting_stops_counting_towards_the_score(self):
        from datetime import datetime, time
        from risk import scoring
        now = timezone.make_aware(datetime.combine(self.today, time(12, 0)))
        self.assertEqual(scoring.supervision_indicator(self.student, self.today), 0.0)   # met today, all fine
        Action.objects.create(meeting=self.meeting, description="Send the draft")
        self.assertEqual(scoring.actions_indicator(self.student), 1.0)
        self.client.login(username="sup", password="x")
        self.client.post(reverse("meeting_review", args=[self.meeting.id]), {"decision": "rejected"})
        self.assertGreater(scoring.supervision_indicator(self.student, self.today), 0.0)  # back to no meeting at all
        self.assertEqual(scoring.actions_indicator(self.student), 0.0)                   # its actions are dropped too
        self.assertIn("supervision", scoring.compute(self.student, now)["breakdown"])

    def test_student_is_told_when_a_meeting_was_rejected(self):
        self.client.login(username="sup", password="x")
        self.client.post(reverse("meeting_review", args=[self.meeting.id]), {"decision": "rejected"})
        self.client.login(username="stu", password="x")
        self.assertContains(self.client.get(reverse("meetings")), "marked this meeting as not held")
        self.assertContains(self.client.get(reverse("student_home")), "as not held, record the real one")

    def test_an_unknown_decision_is_refused(self):
        self.client.login(username="sup", password="x")
        response = self.client.post(reverse("meeting_review", args=[self.meeting.id]), {"decision": "deleted"})
        self.assertEqual(response.status_code, 403)


class ReportTests(TestCase):
    """The printable progress report and who may open it."""

    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        self.student = User.objects.create_user("stu", role="student", password="x", supervisor=self.supervisor,
                                                first_name="Zahra", last_name="Mahmood", student_id="202300001")
        Deliverable.objects.create(title="Reflection 1", order=1, due_at=timezone.now() - timedelta(days=1))
        Meeting.objects.create(student=self.student, held_on=timezone.localdate(), discussed="Agreed the scope")
        for days, score in ((2, 10), (1, 25), (0, 40)):
            RiskScore.objects.create(student=self.student, scored_on=timezone.localdate() - timedelta(days=days),
                                     score=score, status="green" if score < 30 else "amber", breakdown={})
        self.url = reverse("student_report", args=[self.student.id])

    def test_supervisor_gets_the_whole_picture_on_one_page(self):
        self.client.login(username="sup", password="x")
        response = self.client.get(self.url)
        for text in ("CLP progress report", "Zahra Mahmood", "202300001", "Reflection 1", "Missing", "Agreed the scope", "Print or save as PDF"):
            self.assertContains(response, text)
        self.assertEqual(response.context["chart"]["points"], "0.0,108.0 320.0,90.0 640.0,72.0")   # three scores, left to right

    def test_student_can_print_their_own_but_not_someone_elses(self):
        other = User.objects.create_user("stu2", role="student", password="x")
        self.client.login(username="stu", password="x")
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(reverse("student_report", args=[other.id])).status_code, 403)

    def test_another_supervisor_cannot_open_it_and_the_coordinator_can(self):
        User.objects.create_user("sup2", role="supervisor", password="x")
        User.objects.create_user("coord", role="coordinator", password="x")
        self.client.login(username="sup2", password="x")
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.login(username="coord", password="x")
        self.assertEqual(self.client.get(self.url).status_code, 200)


class ScoreFollowsTheRecordsTests(TestCase):
    """The colour on screen is worked out again the moment a record changes, not only the next morning."""

    def test_uploading_overdue_work_changes_the_score_straight_away(self):
        from risk import scoring
        supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        student = User.objects.create_user("stu", role="student", password="x", supervisor=supervisor)
        overdue = Deliverable.objects.create(title="Reflection 1", order=1, due_at=timezone.now() - timedelta(hours=3))
        before = scoring.save_today(student)["score"]
        self.client.login(username="stu", password="x")
        pdf = SimpleUploadedFile("r1.pdf", b"%PDF-1.4 late but in", content_type="application/pdf")
        self.client.post(reverse("submit", args=[overdue.id]), {"file": pdf})
        after = RiskScore.objects.get(student=student, scored_on=timezone.localdate())
        self.assertLess(after.score, before)
        self.assertEqual(after.breakdown["overdue"]["points"], 0.0)
        self.assertEqual(RiskScore.objects.filter(student=student).count(), 1)   # today's row was replaced, not added
