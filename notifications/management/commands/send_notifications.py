"""Sends today's reminders and alerts.  Run with:  python manage.py send_notifications"""
from django.core.management.base import BaseCommand

from notifications import emails


class Command(BaseCommand):
    help = "Send deadline reminders to students and status alerts to supervisors"

    def handle(self, *args, **options):
        reminders = emails.send_deadline_reminders()
        alerts = emails.send_status_alerts()
        self.stdout.write(f"{reminders} reminders and {alerts} alerts sent")
