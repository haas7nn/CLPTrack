"""Loads a development cohort with a few weeks of history, for development and demonstrations.

Run with:  python manage.py seed_cohort --password <a password for the development accounts>

Six students under one supervisor, each with a different story: on time, a bit late, missing work,
meetings held or not. Events are created day by day from three weeks ago to today, and the score is
computed and stored for each day, so the history chart is consistent with the records.
Safe to run twice: it only adds what is missing.
"""
import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from progress.models import Action, Deliverable, Feedback, Meeting, Submission
from risk.models import RiskScore
from risk.scoring import compute

# username, first, last, student id
STUDENTS = [
    ("student1", "Sara", "Ahmed", "202300001"),
    ("student2", "Ali", "Hasan", "202300002"),
    ("student3", "Noor", "Yusuf", "202300003"),
    ("student4", "Maryam", "Khalid", "202300004"),
    ("student5", "Yousif", "Abdulla", "202300005"),
    ("student6", "Reem", "Salman", "202300006"),
]

# Each story is a list of events as (days before today, kind, detail).
# kind "submit": detail is (deliverable order, note)
# kind "meeting": detail is (discussed, [actions], [which action indexes get done later, days before today])
# kind "feedback": detail is text
STORIES = {
    "student1": [
        (6, "submit", (1, "Week one reflection")),
        (5, "meeting", ("Agreed the scope and the first three tasks", ["Send proposal draft", "Set up repository", "Read two sources"], [(0, 3), (1, 2)])),
        (2, "submit", (2, "Proposal draft for comments")),
        (1, "feedback", "Good draft. Tighten the objectives and add the risk table."),
    ],
    "student2": [
        (1, "submit", (1, "")),
        (12, "meeting", ("Discussed the topic options", ["Choose a topic", "Write one page summary"], [])),
    ],
    "student3": [],
    "student4": [
        (7, "submit", (1, "")),
        (12, "meeting", ("First meeting, expectations and dates", ["Prepare concept note"], [(0, 9)])),
        (5, "meeting", ("Reviewed the concept note", ["Expand the requirements", "Draw the architecture"], [(0, 2)])),
        (3, "submit", (2, "Proposal, first full version")),
        (3, "feedback", "Clear and well structured. Check the deadline table against Moodle."),
    ],
    "student5": [
        (2, "submit", (1, "Sorry for the delay")),
        (16, "meeting", ("Discussed the project idea", ["Send the idea in writing", "List the technologies", "Book the next meeting"], [(0, 10)])),
    ],
    "student6": [
        (6, "submit", (1, "")),
    ],
}


class Command(BaseCommand):
    help = "Create a development cohort with three weeks of history"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=os.environ.get("SEED_PASSWORD", ""))
        parser.add_argument("--days", type=int, default=21, help="how many days of history to build")

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError("Give --password or set SEED_PASSWORD, the development accounts need one")
        deliverables = {d.order: d for d in Deliverable.objects.all()}
        if not deliverables:
            raise CommandError("Run seed_deliverables first")

        supervisor, created = User.objects.get_or_create(username="supervisor1", defaults={
            "role": User.Role.SUPERVISOR, "first_name": "Demo", "last_name": "Supervisor",
            "email": "supervisor1@example.com"})
        if created:
            supervisor.set_password(password)
            supervisor.save()

        students = {}
        for username, first, last, sid in STUDENTS:
            user, created = User.objects.get_or_create(username=username, defaults={
                "role": User.Role.STUDENT, "first_name": first, "last_name": last, "student_id": sid,
                "section": "8", "supervisor": supervisor, "email": f"{username}@example.com"})
            if created:
                user.set_password(password)
                user.save()
            students[username] = user

        if RiskScore.objects.filter(student=students["student6"]).exists():
            self.stdout.write("development cohort already has history, nothing added")
            return

        now = timezone.now()
        days = options["days"]
        # walk day by day so each day's score only sees what existed by then
        for back in range(days, -1, -1):
            day = now - timedelta(days=back)
            for username, events in STORIES.items():
                student = students[username]
                for when, kind, detail in events:
                    if when != back:
                        continue
                    if kind == "submit":
                        order, note = detail
                        d = deliverables.get(order)
                        if d and not Submission.objects.filter(student=student, deliverable=d).exists():
                            Submission.objects.create(student=student, deliverable=d, filename=f"{d.title.lower().replace(' ', '_')}.pdf",
                                                      content_type="application/pdf", size=11,
                                                      data=b"%PDF-1.4", note=note, submitted_at=day)
                    elif kind == "meeting":
                        discussed, actions, done_later = detail
                        m = Meeting.objects.create(student=student, held_on=day.date(), discussed=discussed)
                        rows = [Action.objects.create(meeting=m, description=a) for a in actions]
                        for idx, done_back in done_later:
                            rows[idx].done = True
                            rows[idx].done_at = now - timedelta(days=done_back)
                            rows[idx].save()
                    elif kind == "feedback":
                        Feedback.objects.create(supervisor=supervisor, student=student, text=detail, created_at=day)
            for student in students.values():
                result = compute(student, now=day)
                RiskScore.objects.update_or_create(student=student, scored_on=day.date(), defaults={
                    "score": result["score"], "status": result["status"], "breakdown": result["breakdown"]})

        self.stdout.write(f"development cohort ready: {len(students)} students, {days + 1} days of scores")
