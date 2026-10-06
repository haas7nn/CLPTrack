"""Makes a few pretend accounts so we can try the site without real people.

Run with:  python manage.py seed_demo
Creates one coordinator, one supervisor and three students, all with the
password written in DEV_PASSWORD below. Development use only. It is safe to run twice.
"""
from django.core.management.base import BaseCommand

from accounts.models import User

DEV_PASSWORD = "clptrack-dev"

ACCOUNTS = [
    # username, role, first name, last name, student id, section
    ("coordinator", User.Role.COORDINATOR, "Demo", "Coordinator", "", ""),
    ("supervisor1", User.Role.SUPERVISOR, "Demo", "Supervisor", "", ""),
    ("student1", User.Role.STUDENT, "Sara", "Ahmed", "202300001", "8"),
    ("student2", User.Role.STUDENT, "Ali", "Hasan", "202300002", "8"),
    ("student3", User.Role.STUDENT, "Noor", "Yusuf", "202300003", "8"),
]


class Command(BaseCommand):
    help = "Create sample accounts for development"

    def handle(self, *args, **options):
        supervisor = None
        for username, role, first, last, student_id, section in ACCOUNTS:
            user, created = User.objects.get_or_create(username=username, defaults={
                "role": role, "first_name": first, "last_name": last,
                "student_id": student_id, "section": section, "email": f"{username}@example.com",
            })
            if created:
                user.set_password(DEV_PASSWORD)
                if role == User.Role.COORDINATOR:
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
            if role == User.Role.SUPERVISOR:
                supervisor = user
        User.objects.filter(role=User.Role.STUDENT, supervisor__isnull=True).update(supervisor=supervisor)
        self.stdout.write(f"{len(ACCOUNTS)} sample accounts ready, password {DEV_PASSWORD}")
