"""Everyone who can sign in.

One table for all of them. The role field says if someone is a student, a supervisor
or a coordinator, and a student also points at their supervisor.
"""
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Someone who can do everything is a coordinator, so they are not scored like a student."""
        extra_fields.setdefault("role", "coordinator")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """One person. Student, supervisor or coordinator."""

    objects = UserManager()

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        SUPERVISOR = "supervisor", "Supervisor"
        COORDINATOR = "coordinator", "Coordinator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    student_id = models.CharField(max_length=20, blank=True, help_text="Polytechnic student ID, students only")
    section = models.CharField(max_length=10, blank=True, help_text="CLP section, students only")
    supervisor = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="students", limit_choices_to={"role": "supervisor"},
        help_text="The supervisor of this student, students only",
    )

    # set when the coordinator gives someone a first password, cleared when they choose their own
    must_change_password = models.BooleanField(default=False)

    # a student added after the semester started: deadlines before this date were handled on Moodle,
    # so they are not counted as missing. Empty means every deadline counts.
    tracked_from = models.DateField(null=True, blank=True,
                                    help_text="Students only. Deadlines before this date are not counted as missing.")

    def __str__(self):
        name = self.get_full_name() or self.username
        return f"{name} ({self.get_role_display()})"

    def counts(self, deliverable):
        """Is this deliverable one the student is expected to hand in through CLPTrack?"""
        return not self.tracked_from or timezone.localdate(deliverable.due_at) >= self.tracked_from

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_supervisor(self):
        return self.role == self.Role.SUPERVISOR

    @property
    def is_coordinator(self):
        return self.role == self.Role.COORDINATOR
