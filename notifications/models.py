"""A record of every email the system sends, so we can see what went out and when."""
from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    """One email that was sent: to whom, about what, and when."""

    class Kind(models.TextChoices):
        REMINDER = "reminder", "Deadline reminder"
        ALERT = "alert", "Status alert"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    subject = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Stops the same email going twice")

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.get_kind_display()} to {self.recipient} at {self.sent_at:%d %b %H:%M}"
