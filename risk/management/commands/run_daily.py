"""The one command the host runs every day: score everyone, then send the emails."""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Score all students and send notifications, once a day"

    def handle(self, *args, **options):
        call_command("score_students")
        call_command("send_notifications")
