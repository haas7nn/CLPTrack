"""Tests for the accounts app."""
from django.test import TestCase

from accounts.models import User


class EnsureAdminTests(TestCase):
    def test_creates_coordinator_once_from_environment(self):
        from unittest import mock
        from django.core.management import call_command
        env = {"ADMIN_USERNAME": "boss", "ADMIN_EMAIL": "boss@example.com", "ADMIN_PASSWORD": "pw-for-test-only"}
        with mock.patch.dict("os.environ", env):
            call_command("ensure_admin")
            call_command("ensure_admin")
        user = User.objects.get(username="boss")
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, "coordinator")
        self.assertEqual(User.objects.filter(username="boss").count(), 1)

    def test_does_nothing_without_the_variables(self):
        from unittest import mock
        from django.core.management import call_command
        with mock.patch.dict("os.environ", {"ADMIN_USERNAME": "", "ADMIN_PASSWORD": ""}):
            call_command("ensure_admin")
        self.assertFalse(User.objects.filter(is_superuser=True).exists())


class SeedCohortTests(TestCase):
    def test_builds_six_students_with_history_and_is_safe_to_rerun(self):
        from django.core.management import call_command
        from progress.models import Submission, Meeting
        from risk.models import RiskScore
        call_command("seed_deliverables")
        call_command("seed_cohort", password="pw-for-test-only", days=5)
        call_command("seed_cohort", password="pw-for-test-only", days=5)
        self.assertEqual(User.objects.filter(role="student").count(), 6)
        self.assertEqual(RiskScore.objects.filter(student__username="student1").count(), 6)
        self.assertTrue(Submission.objects.filter(student__username="student1").exists())
        self.assertTrue(Meeting.objects.filter(student__username="student4").exists())
        self.assertFalse(RiskScore.objects.filter(student__username="student3", status="green").exists())


class SharedPasswordTests(TestCase):
    def test_sets_the_development_accounts_and_leaves_everyone_else(self):
        from django.core.management import call_command
        from accounts.models import User
        User.objects.create_user("supervisor1", role="supervisor", password="old-one-123")
        User.objects.create_user("student1", role="student", password="old-one-123")
        tester = User.objects.create_user("realtester", role="student", password="their-own-123")
        call_command("shared_password", password="one-for-all-456")
        self.assertTrue(User.objects.get(username="supervisor1").check_password("one-for-all-456"))
        self.assertTrue(User.objects.get(username="student1").check_password("one-for-all-456"))
        tester.refresh_from_db()
        self.assertTrue(tester.check_password("their-own-123"))  # a real tester keeps their own
        coordinator = User.objects.get(username="coordinator")   # made because it was missing
        self.assertTrue(coordinator.is_superuser and coordinator.check_password("one-for-all-456"))

    def test_refuses_a_short_password(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from accounts.models import User
        User.objects.create_user("student1", role="student", password="old-one-123")
        with self.assertRaises(CommandError):
            call_command("shared_password", password="short")
        self.assertTrue(User.objects.get(username="student1").check_password("old-one-123"))


class PasswordTests(TestCase):
    """Changing a password, the first password rule, and the forgotten password email."""

    def setUp(self):
        self.user = User.objects.create_user("stu", role="student", password="first-pass-123", email="stu@example.com")

    def test_user_changes_their_own_password(self):
        from django.urls import reverse
        self.client.login(username="stu", password="first-pass-123")
        response = self.client.post(reverse("password_change"), {
            "old_password": "first-pass-123", "new_password1": "my-own-choice-789", "new_password2": "my-own-choice-789"})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("my-own-choice-789"))

    def test_first_password_must_be_changed_before_anything_else(self):
        from django.urls import reverse
        self.user.must_change_password = True
        self.user.save()
        self.client.login(username="stu", password="first-pass-123")
        self.assertRedirects(self.client.get(reverse("student_home")), reverse("password_change"))
        self.assertContains(self.client.get(reverse("password_change")), "You were given a first password")
        self.client.post(reverse("password_change"), {
            "old_password": "first-pass-123", "new_password1": "my-own-choice-789", "new_password2": "my-own-choice-789"})
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertEqual(self.client.get(reverse("student_home")).status_code, 200)   # now the site opens

    def test_forgotten_password_sends_a_link_that_works_once(self):
        import re
        from django.core import mail
        from django.urls import reverse
        self.assertContains(self.client.get(reverse("login")), "Forgot your password?")
        self.client.post(reverse("password_reset"), {"email": "stu@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Your username is stu", mail.outbox[0].body)
        link = re.search(r"https?://[^\s]+(/accounts/reset/[^\s]+)", mail.outbox[0].body).group(1)
        form_page = self.client.get(link, follow=True)
        self.assertContains(form_page, "Choose a new password")
        self.client.post(form_page.request["PATH_INFO"], {"new_password1": "brand-new-one-456", "new_password2": "brand-new-one-456"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-new-one-456"))
        self.assertContains(self.client.get(link, follow=True), "already used or is too old")

    def test_unknown_email_gets_the_same_answer_and_no_email(self):
        from django.core import mail
        from django.urls import reverse
        response = self.client.post(reverse("password_reset"), {"email": "nobody@example.com"}, follow=True)
        self.assertContains(response, "Check your email")
        self.assertEqual(len(mail.outbox), 0)


class ImportPeopleTests(TestCase):
    """The coordinator loads a cohort from a csv file."""

    def setUp(self):
        from django.urls import reverse
        self.url = reverse("import_people")
        User.objects.create_user("coord", role="coordinator", password="x")
        self.client.login(username="coord", password="x")

    def upload(self, text, password="first-pass-2026"):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return self.client.post(self.url, {"file": SimpleUploadedFile("people.csv", text.encode()), "first_password": password})

    def test_creates_supervisors_then_students_and_links_them(self):
        response = self.upload("username,first_name,last_name,role,student_id,section,supervisor\n"
                               "202300101,Khalid,Jasim,student,202300101,8,dr.salem\n"     # the student comes first on purpose
                               "dr.salem,Huda,Salem,supervisor,,,\n")
        self.assertEqual(response.context["result"]["counts"], {"student": 1, "supervisor": 1, "coordinator": 0})
        student = User.objects.get(username="202300101")
        self.assertEqual(student.supervisor.username, "dr.salem")
        self.assertTrue(student.must_change_password and student.check_password("first-pass-2026"))

    def test_someone_who_already_has_an_account_is_left_alone(self):
        User.objects.create_user("dr.salem", role="supervisor", password="their-own-123", first_name="Huda")
        response = self.upload("username,role,first_name\ndr.salem,supervisor,Changed\nnew.one,supervisor,New\n")
        self.assertEqual(response.context["result"]["skipped"], ["dr.salem"])
        existing = User.objects.get(username="dr.salem")
        self.assertTrue(existing.first_name == "Huda" and existing.check_password("their-own-123"))
        self.assertTrue(User.objects.filter(username="new.one").exists())

    def test_one_bad_line_means_nothing_is_added(self):
        response = self.upload("username,role,supervisor\ngood.one,supervisor,\nbad.one,teacher,\nlost.one,student,nobody\n")
        self.assertContains(response, "Nothing was added")
        self.assertContains(response, "Line 3: the role of bad.one must be student, supervisor or coordinator.")
        self.assertContains(response, "Line 4: the supervisor nobody is not an account and is not in the file.")
        self.assertFalse(User.objects.filter(username="good.one").exists())

    def test_file_without_the_required_columns_is_refused(self):
        response = self.upload("name,job\nKhalid,student\n")
        self.assertContains(response, "Missing: username, role.")

    def test_only_the_coordinator_can_add_people(self):
        from django.urls import reverse
        User.objects.create_user("sup", role="supervisor", password="x")
        self.client.login(username="sup", password="x")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(reverse("import_example")).status_code, 403)
