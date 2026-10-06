from django.contrib import admin

from .models import RiskScore


@admin.register(RiskScore)
class RiskScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "scored_on", "score", "status")
    list_filter = ("status", "scored_on")
