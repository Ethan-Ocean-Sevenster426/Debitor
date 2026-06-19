"""Django email backend that sends through Microsoft Graph (app-only).

Pointing ``EMAIL_BACKEND`` at this class routes ALL Django mail — the built-in
password-reset emails, ``django.core.mail.send_mail``, ``EmailMessage.send()``
and our own ``xero_app.mailer.send_app_email()`` — through the Microsoft Graph
``sendMail`` API using the EPVS Mailing app registration (client-credentials /
``Mail.Send`` application permission). No SMTP, no mailbox license.

Mail is always sent *as* ``settings.MS_GRAPH_SENDER`` (the shared mailbox).
"""
import base64
import logging
import time

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SENDMAIL_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

# Module-level token cache (Graph app tokens last ~1h; reused across sends).
_token_cache = {"value": None, "expires_at": 0.0}


def email_configured():
    """True when all Graph credentials needed to send are present."""
    return all([
        getattr(settings, "MS_GRAPH_TENANT_ID", ""),
        getattr(settings, "MS_GRAPH_CLIENT_ID", ""),
        getattr(settings, "MS_GRAPH_CLIENT_SECRET", ""),
        getattr(settings, "MS_GRAPH_SENDER", ""),
    ])


def _get_token():
    """Fetch (and cache) an app-only access token for Microsoft Graph."""
    now = time.time()
    cached = _token_cache["value"]
    if cached and _token_cache["expires_at"] - 60 > now:
        return cached
    resp = requests.post(
        _TOKEN_URL.format(tenant=settings.MS_GRAPH_TENANT_ID),
        data={
            "client_id": settings.MS_GRAPH_CLIENT_ID,
            "client_secret": settings.MS_GRAPH_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=getattr(settings, "EMAIL_TIMEOUT", 20),
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = now + int(data.get("expires_in", 3600))
    return _token_cache["value"]


def _recipients(addresses):
    return [{"emailAddress": {"address": a}} for a in addresses if a]


def _message_to_graph(message):
    """Convert a Django EmailMessage into a Graph sendMail message dict."""
    # Prefer an HTML alternative if the caller attached one, else plain text.
    content_type, content = "Text", message.body or ""
    for alt_content, alt_mime in getattr(message, "alternatives", None) or []:
        if alt_mime == "text/html":
            content_type, content = "HTML", alt_content
            break

    graph = {
        "subject": message.subject or "",
        "body": {"contentType": content_type, "content": content},
        "toRecipients": _recipients(message.to),
    }
    if message.cc:
        graph["ccRecipients"] = _recipients(message.cc)
    if message.bcc:
        graph["bccRecipients"] = _recipients(message.bcc)
    if getattr(message, "reply_to", None):
        graph["replyTo"] = _recipients(message.reply_to)

    attachments = []
    for att in message.attachments or []:
        # Django attachments are (filename, content, mimetype) tuples on older
        # versions and an EmailAttachment dataclass on newer ones — handle both.
        if isinstance(att, (tuple, list)) and len(att) == 3:
            name, raw, mimetype = att
        elif hasattr(att, "content") and hasattr(att, "filename"):
            name, raw, mimetype = att.filename, att.content, getattr(att, "mimetype", None)
        else:
            continue
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": name or "attachment",
            "contentType": mimetype or "application/octet-stream",
            "contentBytes": base64.b64encode(raw).decode(),
        })
    if attachments:
        graph["attachments"] = attachments
    return graph


class GraphEmailBackend(BaseEmailBackend):
    """Send Django ``EmailMessage`` objects via Microsoft Graph ``sendMail``."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not email_configured():
            msg = "Microsoft Graph email is not configured (MS_GRAPH_* missing)."
            if self.fail_silently:
                logger.warning(msg)
                return 0
            raise RuntimeError(msg)

        sender = settings.MS_GRAPH_SENDER
        try:
            token = _get_token()
        except Exception:
            logger.exception("Graph token request failed")
            if self.fail_silently:
                return 0
            raise

        sent = 0
        for message in email_messages:
            recipients = (message.to or []) + (message.cc or []) + (message.bcc or [])
            if not recipients:
                continue
            try:
                resp = requests.post(
                    _SENDMAIL_URL.format(sender=sender),
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"},
                    json={"message": _message_to_graph(message), "saveToSentItems": True},
                    timeout=getattr(settings, "EMAIL_TIMEOUT", 20),
                )
                if resp.status_code == 202:
                    logger.info("Email sent via Graph to %s — %s",
                                ", ".join(message.to or recipients), message.subject)
                    sent += 1
                else:
                    logger.error("Graph sendMail failed (%s) — %s: %s",
                                 resp.status_code, message.subject, resp.text)
                    if not self.fail_silently:
                        resp.raise_for_status()
            except Exception:
                logger.exception("Graph sendMail error — %s", message.subject)
                if not self.fail_silently:
                    raise
        return sent
