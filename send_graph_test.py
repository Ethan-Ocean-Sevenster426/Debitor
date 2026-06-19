"""One-off test: send an email via Microsoft Graph (app-only / client credentials)
from the accounts@afsq.co.za shared mailbox, using the "EPVS Mailing" app
registration. Confirms the app can get a token AND actually send.

Usage:
    python send_graph_test.py [recipient]

Default recipient: anthony.penzes@moc-pty.com

Reads MS_GRAPH_TENANT_ID / MS_GRAPH_CLIENT_ID / MS_GRAPH_CLIENT_SECRET /
MS_GRAPH_SENDER from the .env file next to manage.py.
"""
import base64
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

TENANT = os.environ.get("MS_GRAPH_TENANT_ID", "")
CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MS_GRAPH_CLIENT_SECRET", "")
SENDER = os.environ.get("MS_GRAPH_SENDER", "accounts@afsq.co.za")

RECIPIENT = sys.argv[1] if len(sys.argv) > 1 else "anthony.penzes@moc-pty.com"


def _roles_in_token(token):
    """Best-effort decode of the access token to show which app roles (Graph
    application permissions) were actually granted — e.g. 'Mail.Send'."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # pad to a multiple of 4
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("roles", [])
    except Exception:
        return None


def main():
    missing = [k for k, v in {
        "MS_GRAPH_TENANT_ID": TENANT,
        "MS_GRAPH_CLIENT_ID": CLIENT_ID,
        "MS_GRAPH_CLIENT_SECRET": CLIENT_SECRET,
    }.items() if not v]
    if missing:
        print("Missing .env values:", ", ".join(missing))
        sys.exit(1)

    print(f"Tenant   : {TENANT}")
    print(f"Client   : {CLIENT_ID}")
    print(f"Sender   : {SENDER}")
    print(f"Recipient: {RECIPIENT}")
    print("-" * 60)

    # 1) client-credentials token from Entra
    print("Requesting app-only token ...")
    token_resp = requests.post(
        f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    if token_resp.status_code != 200:
        print(f"TOKEN REQUEST FAILED ({token_resp.status_code}):")
        print(token_resp.text)
        sys.exit(1)

    token = token_resp.json()["access_token"]
    roles = _roles_in_token(token)
    print("Token acquired OK.")
    print(f"Granted app roles: {roles}")
    if roles is not None and "Mail.Send" not in roles:
        print("  !! 'Mail.Send' is NOT in the token's roles. The send will likely 403.")
        print("     Fix: EPVS Mailing -> API permissions -> add Microsoft Graph ->")
        print("     Application permission 'Mail.Send' -> Grant admin consent.")
    print("-" * 60)

    # 2) send mail AS the shared mailbox
    print(f"Sending test mail as {SENDER} ...")
    send_resp = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{SENDER}/sendMail",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "message": {
                "subject": "FSA Debtor System — Graph test email",
                "body": {
                    "contentType": "Text",
                    "content": (
                        "This is a test message sent via Microsoft Graph "
                        f"from {SENDER} using the EPVS Mailing app registration.\n\n"
                        "If you are reading this, app-only Graph sending works "
                        "and the FSA Debtor System can send mail."
                    ),
                },
                "toRecipients": [{"emailAddress": {"address": RECIPIENT}}],
            },
            "saveToSentItems": True,
        },
        timeout=30,
    )

    if send_resp.status_code == 202:
        print(f"SUCCESS - Email queued to {RECIPIENT} from {SENDER}. (HTTP 202)")
    else:
        print(f"SEND FAILED ({send_resp.status_code}):")
        print(send_resp.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
