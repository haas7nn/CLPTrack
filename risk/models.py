"""The daily risk score of each student.

One row is saved per student per day, so the history can be charted later.
The score itself is calculated in risk/scoring.py.
"""
from django.conf import settings
from django.db import models


class RiskScore(models.Model):
    """The risk score of one student on one day, with the indicators behind it."""

    class Status(models.TextChoices):
        GREEN = "green", "Green"
        AMBER = "amber", "Amber"
        RED = "red", "Red"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_scores")
    scored_on = models.DateField()
    score = models.PositiveSmallIntegerField(help_text="0 to 100")
    status = models.CharField(max_length=10, choices=Status.choices)
    breakdown = models.JSONField(default=dict, help_text="Each indicator and the points it contributed")

    class Meta:
        ordering = ["-scored_on"]
        unique_together = [("student", "scored_on")]

    def __str__(self):
        return f"{self.student} on {self.scored_on}: {self.score} ({self.status})"
