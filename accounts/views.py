"""Changing and resetting passwords.

Django already has these pages. We only add one thing: when a person chooses their own password,
the "must change password" mark the coordinator put on their account is removed.
"""
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy


class ChangePassword(auth_views.PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        form.user.must_change_password = False
        messages.success(self.request, "Your password was changed.")
        return super().form_valid(form)


class ResetConfirm(auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy("password_reset_complete")

    def form_valid(self, form):
        form.user.must_change_password = False
        return super().form_valid(form)
