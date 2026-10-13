"""Changing and resetting passwords, and adding many people from a file.

Django already has these pages. We only add one thing: when a person chooses their own password,
the "must change password" mark the coordinator put on their account is removed.
"""
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy

from dashboard.views import role_required
from . import importer
from .forms import ImportForm


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


@role_required("coordinator")
def import_people(request):
    """The coordinator uploads a csv of students and supervisors and their accounts are created together."""
    form = ImportForm(request.POST or None, request.FILES or None)
    result = problems = None
    if request.method == "POST" and form.is_valid():
        rows, problems = importer.read_rows(form.cleaned_data["file"])
        if not problems:
            new, skipped, problems = importer.check_rows(rows)
            if not problems:
                result = {"counts": importer.create_accounts(new, form.cleaned_data["first_password"]), "skipped": skipped}
                result["total"] = sum(result["counts"].values())
                form = ImportForm()
    return render(request, "accounts/import_people.html", {
        "form": form, "result": result, "problems": problems, "example": importer.EXAMPLE})


@role_required("coordinator")
def import_example(request):
    """An example file to fill in."""
    response = HttpResponse(importer.EXAMPLE, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="clptrack_people_example.csv"'
    return response
