"""One web address that runs the daily job.

The free host has no scheduler, so a GitHub workflow calls this address once a day
with a secret token. Without the right token nothing happens.
"""
import hmac

from django.conf import settings
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
