"""The pages and addresses that belong to the score.

run_daily and test_email are addresses a GitHub workflow calls with a secret token, because the
free host has no scheduler. Without the right token nothing happens.
score_settings is the coordinator's page for the weights and cut off points, with a preview.
"""
import hmac

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import User
from dashboard.views import role_required
from notifications.emails import send_status_alerts
from . import scoring
from .forms import ScoreSettingsForm
from .models import ScoreSettings


def token_is_right(request):
    """True only when the caller sent the secret token. An empty token switches the address off."""
    expected = settings.DAILY_TASK_TOKEN
    given = request.headers.get("X-Task-Token", "")
    # compare_digest stops someone guessing the token one character at a time
    return bool(expected) and hmac.compare_digest(expected.encode(), given.encode())


@csrf_exempt
@require_POST
def run_daily(request):
    if not token_is_right(request):
        return HttpResponseForbidden("no")
    call_command("run_daily")
    return HttpResponse("done")


@csrf_exempt
@require_POST
def test_email(request):
    """Sends one test email to the address given, so the mail settings can be checked after a deploy.

    Needs the same token as the daily job. The address is taken from the request body (field "to").
    """
    if not token_is_right(request):
        return HttpResponseForbidden("no")
    to = request.POST.get("to", "")
    if not to:
        return HttpResponse("give an address in the field named to", status=400)
    try:
        sent = send_mail("CLPTrack test email", "If you can read this, the live site can send email.\n\nCLPTrack",
                         settings.DEFAULT_FROM_EMAIL, [to])
    except Exception as e:  # say what went wrong instead of a bare 500, the host has no shell to look
        detail = getattr(e, "reason", "") or ""
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read().decode()[:300]
            except Exception:
                body = ""
        return HttpResponse(f"failed: {type(e).__name__}: {e} {detail} {body}"[:600], status=502)
    return HttpResponse(f"sent {sent}, backend {settings.MAILERS['default']['BACKEND'].rsplit('.', 1)[-1]}")


@role_required("coordinator")
def score_settings(request):
    """The coordinator sees the weights and cut off points, tries new ones, and saves them.

    Preview works out every student's score with the typed values without saving anything, so the
    coordinator sees who would change colour first. Save stores the values and scores everyone again.
    """
    saved = ScoreSettings.objects.first() or ScoreSettings()
    form = ScoreSettingsForm(request.POST or None, instance=saved)
    preview = None
    if request.method == "POST" and form.is_valid():
        if "save" in request.POST:
            row = form.save(commit=False)
            row.updated_by = request.user
            row.save()
            call_command("score_students")
            send_status_alerts()   # a colour that changed because of the new weights is still a change
            messages.success(request, "The new settings are saved and every student was scored again.")
            return redirect("score_settings")
        preview = what_if(form.cleaned_data)
    return render(request, "risk/score_settings.html", {"form": form, "preview": preview, "saved": saved})


def what_if(data):
    """Every student's score today and with the typed values, side by side. Nothing is saved."""
    new_weights = {name: data[name] for name in ScoreSettings.INDICATORS}
    cutoffs = (data["amber_from"], data["red_from"])
    rows = []
    for student in User.objects.filter(role=User.Role.STUDENT).order_by("last_name", "first_name"):
        now_result = scoring.compute(student)
        new_result = scoring.compute(student, use_weights=new_weights, cutoffs=cutoffs)
        rows.append({"user": student, "now": now_result, "new": new_result,
                     "changed": now_result["status"] != new_result["status"]})
    return {
        "rows": rows,
        "changed": sum(1 for row in rows if row["changed"]),
        "counts": {colour: sum(1 for row in rows if row["new"]["status"] == colour) for colour in ("green", "amber", "red")},
    }
