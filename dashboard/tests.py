"""Tests for the pages. Mostly checking who is allowed to see what."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class PageAccessTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        self.student = User.objects.create_user("stu", role="student", password="x", supervisor=self.supervisor,
                                                first_name="Zahra", last_name="Mahmood")
        self.other_supervisor = User.objects.create_user("sup2", role="supervisor", password="x")

    def test_anonymous_user_is_sent_to_sign_in(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_student_lands_on_the_timeline(self):
        self.client.login(username="stu", password="x")
        response = self.client.get(reverse("home"), follow=True)
        self.assertContains(response, "My CLP timeline")

    def test_student_cannot_open_the_supervisor_page(self):
        self.client.login(username="stu", password="x")
        response = self.client.get(reverse("supervisor_home"))
        self.assertEqual(response.status_code, 403)

    def test_supervisor_sees_only_their_own_students(self):
        self.client.login(username="sup2", password="x")
        response = self.client.get(reverse("supervisor_home"))
        self.assertNotContains(response, "Zahra Mahmood")
        self.client.login(username="sup", password="x")
        response = self.client.get(reverse("supervisor_home"))
        self.assertContains(response, "Zahra Mahmood")


class CoordinatorTests(TestCase):
    def test_coordinator_sees_every_supervisor_and_student_cannot(self):
        coordinator = User.objects.create_user("coord", role="coordinator", password="x")
        sup = User.objects.create_user("supa", role="supervisor", password="x", first_name="Adeeb", last_name="Sulaiman")
        User.objects.create_user("stu9", role="student", password="x", supervisor=sup, first_name="Mona", last_name="Khalil")
        self.client.login(username="coord", password="x")
        response = self.client.get(reverse("coordinator_home"))
        self.assertContains(response, "Adeeb Sulaiman")
        self.assertContains(response, "Mona Khalil")
        self.client.login(username="stu9", password="x")
        self.assertEqual(self.client.get(reverse("coordinator_home")).status_code, 403)


class ExportTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user("sup", role="supervisor", password="x")
        self.other = User.objects.create_user("sup2", role="supervisor", password="x")
        self.coordinator = User.objects.create_user("coord", role="coordinator", password="x")
        User.objects.create_user("stu", role="student", password="x", supervisor=self.supervisor,
                                 first_name="Zahra", last_name="Mahmood", student_id="202300001")
        User.objects.create_user("stu2", role="student", password="x", supervisor=self.other,
                                 first_name="Omar", last_name="Khalid", student_id="202300002")

    def test_supervisor_downloads_only_their_own_students(self):
        self.client.login(username="sup", password="x")
        response = self.client.get(reverse("export_csv"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        text = response.content.decode()
        self.assertIn("202300001,Zahra Mahmood", text)
        self.assertNotIn("Omar Khalid", text)
        self.assertIn("not scored", text)

    def test_coordinator_downloads_everyone(self):
        self.client.login(username="coord", password="x")
        text = self.client.get(reverse("export_csv")).content.decode()
        self.assertIn("Zahra Mahmood", text)
        self.assertIn("Omar Khalid", text)

    def test_student_cannot_download(self):
        self.client.login(username="stu", password="x")
        self.assertEqual(self.client.get(reverse("export_csv")).status_code, 403)


class EarlyUploadTests(TestCase):
    def test_early_upload_is_not_counted_against_due_work(self):
        from datetime import timedelta
        from django.utils import timezone
        from progress.models import Deliverable, Submission
        from dashboard.views import summary_for
        sup = User.objects.create_user("sup", role="supervisor", password="x")
        stu = User.objects.create_user("stu", role="student", password="x", supervisor=sup)
        now = timezone.now()
        due = Deliverable.objects.create(title="Past", order=1, due_at=now - timedelta(days=2))
        later = Deliverable.objects.create(title="Future", order=2, due_at=now + timedelta(days=5))
        Submission.objects.create(student=stu, deliverable=due, filename="a.pdf", data=b"x", submitted_at=now - timedelta(days=3))
        Submission.objects.create(student=stu, deliverable=later, filename="b.pdf", data=b"x", submitted_at=now)
        row = summary_for(stu, now, 1)
        self.assertEqual(row["submitted"], 1)
        self.assertEqual(row["early"], 1)
        self.assertEqual(row["missing"], 0)
