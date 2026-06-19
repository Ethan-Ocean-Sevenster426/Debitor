"""Transactional lawyer notifications (distinct from the weekly digest in
reports.py). Currently: alert the lawyers when a new matter is approved and
becomes active, so they know a new client needs attention.

Sends through the same Graph email path as everything else. Any send failure is
logged and swallowed — a notification must never block the approval itself.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from .mailer import send_app_email
from .models import ReportRecipient

logger = logging.getLogger(__name__)
User = get_user_model()


def _lawyer_recipients():
    """Who to alert: the configured Lawyer Report recipients — the same curated
    "lawyers and management" list as the weekly report, so there's one clean
    place to manage who hears from the lawyers' side. If none are configured yet,
    fall back to active users with the Lawyer role."""
    emails = list(ReportRecipient.objects.filter(is_active=True)
                  .values_list("email", flat=True))
    if emails:
        return emails
    return list(User.objects.filter(role=Role.LAWYER, is_active=True)
                .exclude(email="").values_list("email", flat=True))


def notify_new_matter_approved(matter, approved_by=""):
    """Email the lawyers that a newly handed-over client has been approved and
    needs attention. Returns the number of messages sent (0 if nobody to notify
    or the send failed)."""
    recipients = _lawyer_recipients()
    if not recipients:
        logger.info("New-matter approval for %s: no lawyer/recipient emails to notify.",
                    matter.contact_name or matter.contact_id)
        return 0

    name = matter.contact_name or matter.contact_id
    ctx = {
        "name": name,
        "approved_by": approved_by or matter.approved_by or "",
        "approved_at": matter.approved_at or timezone.now(),
        "url": settings.SITE_BASE_URL + reverse("xero_legal_matter", args=[matter.id]),
        "legal_url": settings.SITE_BASE_URL + reverse("xero_legal"),
    }
    subject = f"New client for the lawyers — {name} needs attention"
    text_body = render_to_string("xero/new_matter_email.txt", ctx)
    html_body = render_to_string("xero/new_matter_email.html", ctx)

    to = [settings.MS_GRAPH_SENDER] if settings.MS_GRAPH_SENDER else [recipients[0]]
    try:
        return send_app_email(subject=subject, body=text_body, to=to,
                              html_body=html_body, bcc=recipients)
    except Exception:
        logger.exception("Failed to send new-matter approval notification for %s", name)
        return 0
