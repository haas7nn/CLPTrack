"""Everything about a student's progress: what is due, what they handed in, what was discussed.

Deliverable  one item every student must hand in, with its deadline
Submission   one file a student uploaded for a deliverable
Meeting      one supervision meeting recorded by a student
Action       one task agreed in a meeting, ticked off when done
Feedback     one written comment from a supervisor to a student
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Deliverable(models.Model):
    """One thing every student has to hand in, like Reflection 2, with its deadline."""

    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField()
    order = models.PositiveIntegerField(default=0, help_text="Position in the list, lowest first")

    class Meta:
        ordering = ["order", "due_at"]

    def __str__(self):
        return self.title

    def is_overdue(self):
        return timezone.now() > self.due_at


class Submission(models.Model):
    """One file a student uploaded for one deliverable."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    deliverable = models.ForeignKey(Deliverable, on_delete=models.CASCADE, related_name="submissions")
    file = models.FileField(upload_to="submissions/%Y/%m/")
    note = models.CharField(max_length=300, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} submitted {self.deliverable}"

    def days_late(self):
        """How many days late this was. 0 means on time."""
        delay = self.submitted_at - self.deliverable.due_at
        return max(0, delay.days)


class Meeting(models.Model):
    """One meeting with the supervisor, written down by the student."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meetings")
    held_on = models.DateField()
    discussed = models.TextField(help_text="What was discussed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-held_on"]

    def __str__(self):
        return f"Meeting of {self.student} on {self.held_on}"


class Action(models.Model):
    """Something the student agreed to do in a meeting. Ticked when done."""

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="actions")
    description = models.CharField(max_length=300)
    done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.description


class Feedback(models.Model):
    """A comment the supervisor leaves for the student."""

    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_given")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_received")
    submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.SET_NULL, related_name="feedback")
    meeting = models.ForeignKey(Meeting, null=True, blank=True, on_delete=models.SET_NULL, related_name="feedback")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback for {self.student} from {self.supervisor}"
