"""Three deadlines were entered wrongly and are corrected here to match the course page on Moodle.

The demonstration slides and the poster are due on 30 December at 08:00. The 27th is the day the upload
opens. The fifth reflection is due at 23:59, not 23:55. A row is only changed if it still holds the old
value, so a date the coordinator edited by hand is left alone.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

BAHRAIN = ZoneInfo("Asia/Bahrain")
FIXES = [
    ("Demonstration and presentation", datetime(2026, 12, 27, 8, 0, tzinfo=BAHRAIN), datetime(2026, 12, 30, 8, 0, tzinfo=BAHRAIN)),
    ("Poster", datetime(2026, 12, 27, 8, 0, tzinfo=BAHRAIN), datetime(2026, 12, 30, 8, 0, tzinfo=BAHRAIN)),
    ("Biweekly Reflection 5", datetime(2026, 11, 28, 23, 55, tzinfo=BAHRAIN), datetime(2026, 11, 28, 23, 59, tzinfo=BAHRAIN)),
]


def correct(apps, schema_editor):
    Deliverable = apps.get_model("progress", "Deliverable")
    for title, old, new in FIXES:
        Deliverable.objects.filter(title=title, due_at=old).update(due_at=new)


class Migration(migrations.Migration):
    dependencies = [("progress", "0004_submission_one_submission_per_deliverable")]
    operations = [migrations.RunPython(correct, migrations.RunPython.noop)]
