"""Admin screens for deliverables, submissions, meetings, actions and feedback."""
from django.contrib import admin

from .models import Action, Deliverable, Feedback, Meeting, Submission


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "due_at")
    ordering = ("order",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("student", "deliverable", "submitted_at", "days_late")
    list_filter = ("deliverable",)


class ActionInline(admin.TabularInline):
    model = Action
    extra = 1


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("student", "held_on")
    inlines = [ActionInline]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("student", "supervisor", "created_at")
