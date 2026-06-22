"""Keep the saved Xero connection available to every logged-in request.

Xero OAuth tokens are persisted once on the ``XeroConnection`` row — the same row
the hourly ``sync_xero`` command uses. This middleware mirrors that row's *current*
access token into each authenticated user's session, refreshing it via the DB when
it is near expiry.

Why this exists
---------------
The views were written to read the Xero token from ``request.session``. That ties
the connection to one browser session, so every logout / session-expiry forced the
user to click "Connect to Xero" again, and each user had to connect separately.

By hydrating the session from the persisted row on every request, once *any* Super
Admin has connected Xero, every user — in every new session, after every logout — is
treated as connected. Nobody has to reconnect.

The DB row is the single source of truth for the (rotating) refresh token, so the web
app and the background sync never refresh from divergent copies — which would
otherwise invalidate each other under Xero's refresh-token rotation.
"""
from .models import XeroConnection
from . import xero_client


class XeroConnectionMiddleware:
    """Mirror the persisted Xero connection into the logged-in user's session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            self._hydrate(request)
        return self.get_response(request)

    @staticmethod
    def _hydrate(request):
        try:
            conn = XeroConnection.objects.order_by("id").first()
            if not conn or not conn.refresh_token:
                return
            # Refreshes against the DB row when within 60s of expiry; otherwise
            # returns the current access token. Never uses the request session.
            token = xero_client._ensure_token(conn)
        except Exception:
            # A token hiccup (network, revoked refresh token) must never break the
            # page. If we can't hydrate, the existing views fall back to the
            # "Connect to Xero" redirect, which re-establishes the DB connection.
            return

        # Only write (and thus mark the session dirty) when something actually
        # changed, so we don't persist the session on every single request.
        session = request.session
        for key, value in (
            ("xero_access_token", token),
            ("xero_refresh_token", conn.refresh_token),
            ("xero_tenant_id", conn.tenant_id),
            ("xero_tenant_name", conn.tenant_name),
        ):
            if session.get(key) != value:
                session[key] = value
