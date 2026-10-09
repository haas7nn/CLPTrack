"""Sends email through Brevo's web API instead of a mail server port.

The host blocks outgoing mail ports, but normal HTTPS always works. Django calls send_messages()
with the emails it wants sent; each one becomes one request to Brevo.
Settings: BREVO_API_KEY (required), DEFAULT_FROM_EMAIL (the verified sender).
"""
import json
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            name, address = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
            payload = {
                "sender": {"email": address, **({"name": name} if name else {})},
                "to": [{"email": to} for to in message.to],
                "subject": message.subject,
                "textContent": message.body,
            }
            request = urllib.request.Request(
                API_URL, data=json.dumps(payload).encode(), method="POST",
                headers={"api-key": settings.BREVO_API_KEY, "content-type": "application/json", "accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    if 200 <= response.status < 300:
                        sent += 1
            except urllib.error.URLError:
                if not self.fail_silently:
                    raise
        return sent
