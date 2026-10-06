"""Works out today's risk score for every student and saves it.

Run with:  python manage.py score_students
The host runs this once a day. Running it twice on the same day just updates today's row.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from risk.models import RiskScore
from risk import scoring


class Command(BaseCommand):
    help = "Calculate and save today's risk score for every student"

    def handle(self, *args, **options):
        today = timezone.localdate()
        for student in User.objects.filter(role=User.Role.STUDENT):
            result = scoring.compute(student)
            RiskScore.objects.update_or_create(
                student=student, scored_on=today,
                defaults={"score": result["score"], "status": result["status"], "breakdown": result["breakdown"]},
            )
            self.stdout.write(f"{student.get_full_name() or student.username}: {result['score']} {result['status']}")
