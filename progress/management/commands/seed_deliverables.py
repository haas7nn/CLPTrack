"""Load the CLP deliverable schedule for the September 2026 semester.

Run with:  python manage.py seed_deliverables
It only adds deliverables that do not exist yet, so it is safe to run twice.
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from progress.models import Deliverable

SCHEDULE = [
    # order, title, year, month, day, hour, minute
    (1, "Weekly Reflection 1", 2026, 10, 3, 23, 55),
    (2, "Project Proposal (all three forms)", 2026, 10, 15, 23, 59),
    (3, "Biweekly Reflection 2", 2026, 10, 17, 23, 55),
    (4, "Biweekly Reflection 3", 2026, 10, 31, 23, 55),
    (5, "Biweekly Reflection 4", 2026, 11, 14, 23, 55),
    (6, "Biweekly Reflection 5", 2026, 11, 28, 23, 55),
    (7, "Employability Skills Reflection", 2026, 12, 5, 23, 59),
    (8, "Thesis", 2026, 12, 19, 23, 55),
    (9, "Demonstration and presentation", 2026, 12, 27, 8, 0),
    (10, "Poster", 2026, 12, 27, 8, 0),
]


class Command(BaseCommand):
    help = "Load the CLP deliverable schedule"

    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        added = 0
        for order, title, y, m, d, hh, mm in SCHEDULE:
            due = timezone.make_aware(datetime(y, m, d, hh, mm), tz)
            _, created = Deliverable.objects.get_or_create(title=title, defaults={"order": order, "due_at": due})
            added += created
        self.stdout.write(f"{added} deliverables added, {len(SCHEDULE)} in total")
