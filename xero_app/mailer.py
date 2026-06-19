"""Convenience helper for sending application email.

Builds a Django email and sends it through the configured backend
(``GraphEmailBackend`` → Microsoft Graph; see ``xero_app/mail_backend.py``).
Keeping every feature — user onboarding, password resets, weekly reports,
debtor reminders — on this one function keeps subject/body/recipient handling
consistent, and means nothing in the app needs to know about Graph directly.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def _as_list(value):
    """Normalise a single address or an iterable of addresses to a clean list."""
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    return [a.strip() for a in value if a and a.strip()]


def send_app_email(subject, body, to, *, html_body=None, from_email=None,
                   cc=None, bcc=None, reply_to=None, attachments=None,
                   fail_silently=False):
    """Send one email from the system mailbox (via Microsoft Graph).

    ``to`` / ``cc`` / ``bcc`` / ``reply_to`` accept a single address string or an
    iterable of addresses. ``attachments`` is an optional list of
    ``(filename, content, mimetype)`` tuples. Returns the number of messages
    delivered (0 or 1).
    """
    recipients = _as_list(to)
    if not recipients:
        logger.warning("send_app_email: no recipient for subject %r — skipped", subject)
        return 0

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        cc=_as_list(cc),
        bcc=_as_list(bcc),
        reply_to=_as_list(reply_to),
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    for attachment in attachments or []:
        msg.attach(*attachment)

    return msg.send(fail_silently=fail_silently)
