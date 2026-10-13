from django.contrib import admin

from .models import RiskScore, ScoreSettings


@admin.register(RiskScore)
class RiskScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "scored_on", "score", "status")
    list_filter = ("status", "scored_on")


@admin.register(ScoreSettings)
class ScoreSettingsAdmin(admin.ModelAdmin):
    list_display = ("overdue", "lateness", "supervision", "proximity", "actions", "amber_from", "red_from", "updated_at")
