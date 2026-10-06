"""Admin screens for users. The admin site is Django's built in back office."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "student_id", "section", "supervisor")
    list_filter = ("role", "section", "supervisor")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("CLP", {"fields": ("role", "student_id", "section", "supervisor")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("CLP", {"fields": ("role", "student_id", "section", "supervisor", "email", "first_name", "last_name")}),
    )
