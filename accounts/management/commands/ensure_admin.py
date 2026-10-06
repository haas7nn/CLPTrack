"""Creates the coordinator account on the host, where there is no shell to do it by hand.

Reads ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD from the environment. Does nothing if
they are not set, and never changes the password of an account that already exists.
"""
import os

from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Create the coordinator superuser from environment variables, if it does not exist"

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")
        if not username or not password:
            self.stdout.write("ADMIN_USERNAME or ADMIN_PASSWORD not set, skipping")
            return
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"{username} already exists")
            return
        User.objects.create_superuser(
            username=username,
            email=os.environ.get("ADMIN_EMAIL", ""),
            password=password,
            role=User.Role.COORDINATOR,
            first_name="CLP",
            last_name="Coordinator",
        )
        self.stdout.write(f"created {username}")
