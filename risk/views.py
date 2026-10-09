"""One web address that runs the daily job.

The free host has no scheduler, so a GitHub workflow calls this address once a day
with a secret token. Without the right token nothing happens.
"""
import hmac

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def run_daily(request):
    expected = getattr(settings, "DAILY_TASK_TOKEN", "")
    given = request.headers.get("X-Task-Token", "")
    # compare_digest stops someone guessing the token one character at a time
    if not expected or not hmac.compare_digest(expected, given):
        return HttpResponseForbidden("no")
    call_command("run_daily")
    return HttpResponse("done")


@csrf_exempt
@require_POST
def test_email(request):
    """Sends one test email to the address given, so the mail settings can be checked after a deploy.

    Needs the same token as the daily job. The address is taken from the request body (field "to").
    """
    expected = getattr(settings, "DAILY_TASK_TOKEN", "")
    given = request.headers.get("X-Task-Token", "")
    if not expected or not hmac.compare_digest(expected, given):
        return HttpResponseForbidden("no")
    to = request.POST.get("to", "")
    if not to:
        return HttpResponse("give an address in the field named to", status=400)
    sent = send_mail("CLPTrack test email", "If you can read this, the live site can send email.\n\nCLPTrack",
                     settings.DEFAULT_FROM_EMAIL, [to])
    return HttpResponse(f"sent {sent}")
