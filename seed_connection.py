"""One-off: copy Xero tokens from the active Django session into XeroConnection.

Run once after migration. Future OAuth callbacks write to XeroConnection directly,
so this script is only needed to bootstrap the existing logged-in session.
"""
import os
import sys
import django
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.contrib.sessions.models import Session
from django.utils import timezone
from xero_app.models import XeroConnection

sess = (
    Session.objects.filter(expire_date__gt=timezone.now())
    .order_by("-expire_date")
    .first()
)
if not sess:
    print("No active session. Authenticate via /xero/login/ first.")
    sys.exit(1)

data = sess.get_decoded()
tenant_id = data.get("xero_tenant_id")
access_token = data.get("xero_access_token")
refresh_token = data.get("xero_refresh_token")
if not (tenant_id and access_token and refresh_token):
    print("Session does not contain Xero tokens. Re-authenticate via /xero/login/.")
    sys.exit(1)

expires_in = int(data.get("xero_token_expires_in", 1800))
conn, created = XeroConnection.objects.update_or_create(
    tenant_id=tenant_id,
    defaults={
        "tenant_name": data.get("xero_tenant_name", ""),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": timezone.now() + timedelta(seconds=expires_in),
    },
)
action = "created" if created else "updated"
print(f"XeroConnection {action}: {conn.tenant_name} ({conn.tenant_id})")
print(f"Token expires at: {conn.token_expires_at}")
