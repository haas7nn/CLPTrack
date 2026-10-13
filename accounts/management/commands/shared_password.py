"""Gives the development accounts one shared password, the same on the laptop and on the host.

Run with:  python manage.py shared_password
On the laptop it asks for the password and hides what you type. On the host it reads the
ACCOUNTS_PASSWORD setting, so the password is never written in the code.

It only touches the accounts named in DEV_USERNAMES. Any other account, such as a real tester,
keeps its own password. If there is no account called coordinator yet, it makes one, so the same
eight usernames work everywhere.
"""
import getpass
import os
import sys

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User

DEV_USERNAMES = ["coordinator", "supervisor1"] + [f"student{n}" for n in range(1, 7)]
MIN_LENGTH = 8


class Command(BaseCommand):
    help = "Set one shared password on the development accounts"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=os.environ.get("ACCOUNTS_PASSWORD", ""))

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            if not sys.stdin.isatty():
                self.stdout.write("ACCOUNTS_PASSWORD not set, skipping")
                return
            password = getpass.getpass("New password for the development accounts: ")
            if password != getpass.getpass("Type it again: "):
                raise CommandError("The two did not match, nothing was changed")
        if len(password) < MIN_LENGTH:
            raise CommandError(f"Use at least {MIN_LENGTH} characters, nothing was changed")

        coordinator, created = User.objects.get_or_create(username="coordinator", defaults={
            "role": User.Role.COORDINATOR, "first_name": "Demo", "last_name": "Coordinator",
            "is_staff": True, "is_superuser": True,
        })
        changed = 0
        for user in User.objects.filter(username__in=DEV_USERNAMES):
            user.set_password(password)
            user.save()
            changed += 1
        made = ", coordinator account created" if created else ""
        self.stdout.write(f"shared password set on {changed} accounts{made}")
