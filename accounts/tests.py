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
