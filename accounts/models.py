"""User accounts for CLPTrack.

There is one User table. The "role" field says what kind of user a person is,
and a student also records who their supervisor is.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A person who can sign in: a student, a supervisor or a coordinator."""

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

    def __str__(self):
        name = self.get_full_name() or self.username
        return f"{name} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_supervisor(self):
        return self.role == self.Role.SUPERVISOR
