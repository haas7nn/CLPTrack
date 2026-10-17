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
        meeting = Meeting.objects.create(student=self.student, held_on=timezone.localdate(now - 16 * day), discussed="plan")
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


class ScoreSettingsTests(TestCase):
    """The page where the coordinator changes the weights and tries them first."""

    def setUp(self):
        from accounts.models import User
        from progress.models import Deliverable
        from datetime import timedelta
        from django.utils import timezone
        self.coordinator = User.objects.create_user("coord", role="coordinator", password="x")
        self.student = User.objects.create_user("stu", role="student", password="x", first_name="Zahra", last_name="Mahmood")
        # one deliverable already due with nothing handed in, so the overdue indicator is at its worst
        Deliverable.objects.create(title="Reflection 1", order=1, due_at=timezone.now() - timedelta(days=2))
        self.values = {"overdue": 35, "lateness": 20, "supervision": 25, "proximity": 10, "actions": 10,
                       "amber_from": 30, "red_from": 60}
        self.client.login(username="coord", password="x")

    def test_only_the_coordinator_can_open_it(self):
        from django.urls import reverse
        self.assertEqual(self.client.get(reverse("score_settings")).status_code, 200)
        self.client.login(username="stu", password="x")
        self.assertEqual(self.client.get(reverse("score_settings")).status_code, 403)

    def test_weights_must_add_up_to_100(self):
        from django.urls import reverse
        from risk.models import ScoreSettings
        response = self.client.post(reverse("score_settings"), dict(self.values, overdue=50, save="1"))
        self.assertContains(response, "must add up to 100")
        self.assertEqual(ScoreSettings.objects.count(), 0)

    def test_preview_shows_who_would_change_and_saves_nothing(self):
        from django.urls import reverse
        from risk.models import ScoreSettings
        tried = dict(self.values, overdue=10, lateness=45, preview="1")   # make missing work matter much less
        response = self.client.post(reverse("score_settings"), tried)
        row = response.context["preview"]["rows"][0]
        self.assertGreater(row["now"]["score"], row["new"]["score"])
        self.assertEqual(response.context["preview"]["changed"], 1)
        self.assertContains(response, "would change colour")
        self.assertEqual(ScoreSettings.objects.count(), 0)

    def test_saving_changes_the_score_and_scores_everyone_again(self):
        from django.urls import reverse
        from risk import scoring
        from risk.models import RiskScore, ScoreSettings
        before = scoring.compute(self.student)["score"]
        response = self.client.post(reverse("score_settings"), dict(self.values, overdue=10, lateness=45, save="1"))
        self.assertRedirects(response, reverse("score_settings"))
        saved = ScoreSettings.objects.get()
        self.assertEqual((saved.overdue, saved.updated_by), (10, self.coordinator))
        self.assertLess(scoring.compute(self.student)["score"], before)
        self.assertEqual(RiskScore.objects.filter(student=self.student).count(), 1)   # scored again straight away

    def test_the_wording_under_the_score_follows_the_cut_off_points(self):
        from django.urls import reverse
        from risk.models import RiskScore, ScoreSettings
        from django.utils import timezone
        ScoreSettings.objects.create(amber_from=25, red_from=50)
        RiskScore.objects.create(student=self.student, scored_on=timezone.localdate(), score=10, status="green", breakdown={})
        self.client.login(username="stu", password="x")
        self.assertContains(self.client.get(reverse("student_home")), "Below 25 green, 25 to 49 amber, 50 and above red.")


class ProximityAndLabelTests(TestCase):
    def setUp(self):
        from accounts.models import User
        self.student = User.objects.create_user("stu", role="student", password="x")

    def test_uploading_for_the_nearest_deadline_does_not_hide_the_next_one(self):
        from datetime import timedelta
        from django.utils import timezone
        from progress.models import Deliverable, Submission
        from risk import scoring
        now = timezone.now()
        near = Deliverable.objects.create(title="Proposal", order=1, due_at=now + timedelta(days=2))
        Deliverable.objects.create(title="Reflection 2", order=2, due_at=now + timedelta(days=4))
        self.assertAlmostEqual(scoring.proximity_indicator(self.student, now), 5 / 7, places=2)
        Submission.objects.create(student=self.student, deliverable=near, filename="p.pdf", submitted_at=now)
        self.assertAlmostEqual(scoring.proximity_indicator(self.student, now), 3 / 7, places=2)   # the second one now counts

    def test_labels_say_one_day_and_today(self):
        from datetime import timedelta
        from django.utils import timezone
        from dashboard.views import timeline_for
        from progress.models import Deliverable, Submission
        now = timezone.now()
        Deliverable.objects.create(title="A", order=1, due_at=now + timedelta(hours=5))
        Deliverable.objects.create(title="B", order=2, due_at=now + timedelta(days=1, hours=5))
        late = Deliverable.objects.create(title="C", order=3, due_at=now - timedelta(days=3))
        Submission.objects.create(student=self.student, deliverable=late, filename="c.pdf",
                                  submitted_at=late.due_at + timedelta(days=1, hours=2))
        labels = {row["deliverable"].title: row["label"] for row in timeline_for(self.student, now)}
        self.assertEqual(labels, {"A": "Due today", "B": "Due in 1 day", "C": "Submitted 1 day late"})

    def test_a_token_with_unusual_characters_is_refused_not_an_error(self):
        from django.test import override_settings
        from django.urls import reverse
        with override_settings(DAILY_TASK_TOKEN="right-token"):
            response = self.client.post(reverse("run_daily"), headers={"X-Task-Token": "s\u00e9cret"})
        self.assertEqual(response.status_code, 403)


class LateAddedStudentTests(TestCase):
    """A student added in the middle of the semester is not blamed for deadlines that passed before."""

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from progress.models import Deliverable
        self.now = timezone.now()
        self.today = timezone.localdate(self.now)
        Deliverable.objects.create(title="Reflection 1", order=1, due_at=self.now - timedelta(days=20))
        Deliverable.objects.create(title="Proposal", order=2, due_at=self.now - timedelta(days=2))
        Deliverable.objects.create(title="Thesis", order=3, due_at=self.now + timedelta(days=30))
        self.sup = User.objects.create_user("sup", role="supervisor", password="x")
        self.added = User.objects.create_user("added", role="student", password="x", supervisor=self.sup,
                                              tracked_from=self.today - timedelta(days=5))
        self.original = User.objects.create_user("orig", role="student", password="x", supervisor=self.sup)

    def test_only_deadlines_after_the_account_count_as_overdue(self):
        from risk.scoring import overdue_indicator
        self.assertEqual(overdue_indicator(self.added, self.now), 1.0)       # only the proposal counts, and it is missing
        self.assertEqual(overdue_indicator(self.original, self.now), 1.0)    # both count, both missing
        self.added.tracked_from = self.today
        self.assertEqual(overdue_indicator(self.added, self.now), 0.0)       # added today: nothing overdue yet

    def test_meeting_gap_counts_from_the_day_they_were_added(self):
        from risk.scoring import supervision_indicator
        self.added.tracked_from = self.today
        self.assertEqual(supervision_indicator(self.added, self.today), 0.0)

    def test_new_student_added_today_is_green(self):
        from risk.scoring import compute
        self.added.tracked_from = self.today
        self.assertEqual(compute(self.added, self.now)["status"], "green")

    def test_timeline_and_bar_show_older_work_as_before_the_account(self):
        from dashboard.views import progress_for, timeline_for
        rows = timeline_for(self.added, self.now)
        self.assertEqual([r["status"] for r in rows], ["before", "missing", "upcoming"])
        self.assertEqual(progress_for(rows), {"done": 0, "total": 2, "percent": 0, "before": 1})

    def test_cohort_counts_do_not_list_them_as_missing_older_work(self):
        from dashboard.views import deliverable_stats
        stats = {r["deliverable"].title: r for r in deliverable_stats([self.added, self.original], self.now)}
        self.assertEqual(stats["Reflection 1"]["missing"], 1)   # only the original student
        self.assertEqual(stats["Proposal"]["missing"], 2)
