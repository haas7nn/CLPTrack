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
