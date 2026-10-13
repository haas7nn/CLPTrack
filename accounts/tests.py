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
