"""One-off diagnostic: reads the active Xero session from Django, then calls
Xero directly with each query strategy and prints counts, totals, and the
date range so we can see what's actually in the open AR set."""
import os
import sys
import django
import requests
from datetime import datetime, date
from collections import Counter
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.contrib.sessions.models import Session
from django.utils import timezone

XERO_API_BASE = "https://api.xero.com/api.xro/2.0"

sess = (
    Session.objects.filter(expire_date__gt=timezone.now())
    .order_by("-expire_date")
    .first()
)
if not sess:
    print("No active session in DB. Open /xero/dashboard/ in the browser first.")
    sys.exit(1)

data = sess.get_decoded()
token = data.get("xero_access_token")
refresh_token = data.get("xero_refresh_token")
tenant = data.get("xero_tenant_id")
tenant_name = data.get("xero_tenant_name")
if not token or not tenant:
    print("Session has no Xero tokens. Re-authenticate via /xero/login/.")
    sys.exit(1)


def refresh_access_token():
    global token
    client_id = os.environ.get("XERO_CLIENT_ID", "")
    client_secret = os.environ.get("XERO_CLIENT_SECRET", "")
    if not client_id or not client_secret or not refresh_token:
        return False
    r = requests.post(
        "https://identity.xero.com/connect/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code == 200:
        token = r.json()["access_token"]
        print(f"  [refreshed access token]")
        return True
    print(f"  [refresh failed: {r.status_code} {r.text[:200]}]")
    return False


print(f"Tenant: {tenant_name} ({tenant})")
headers = {
    "Authorization": f"Bearer {token}",
    "xero-tenant-id": tenant,
    "Accept": "application/json",
}


def fetch_all(query):
    url = f"{XERO_API_BASE}/Invoices?{query}"
    all_inv = []
    page = 1
    refreshed = False
    while True:
        r = requests.get(f"{url}&page={page}", headers=headers, timeout=30)
        if r.status_code == 401 and not refreshed:
            if refresh_access_token():
                headers["Authorization"] = f"Bearer {token}"
                refreshed = True
                continue
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", "5"))
            print(f"  [429] rate-limited; waiting {wait}s")
            import time as _t
            _t.sleep(wait + 0.5)
            continue
        if r.status_code != 200:
            print(f"  [http {r.status_code}] {r.text[:200]}")
            return all_inv, r.status_code
        body = r.json().get("Invoices", []) or []
        if not body:
            break
        all_inv.extend(body)
        if len(body) < 100:
            break
        page += 1
    return all_inv, 200


def summarize(label, invoices):
    print(f"\n--- {label} ---")
    print(f"  count: {len(invoices)}")
    if not invoices:
        return
    dates = []
    statuses = Counter()
    total_due = 0.0
    open_due = 0.0
    open_count = 0
    today = date.today()
    bucket_totals = Counter()
    bucket_counts = Counter()
    for inv in invoices:
        ds = inv.get("DateString") or inv.get("Date") or ""
        try:
            d = datetime.fromisoformat(ds[:19]).date()
            dates.append(d)
        except (ValueError, TypeError):
            pass
        statuses[inv.get("Status", "?")] += 1
        ad = float(inv.get("AmountDue") or 0)
        total_due += ad
        if ad > 0 and inv.get("Status") not in ("PAID", "VOIDED", "DELETED"):
            open_due += ad
            open_count += 1
            due_s = inv.get("DueDateString") or inv.get("DueDate") or ""
            try:
                due = datetime.fromisoformat(due_s[:19]).date()
                dpd = (today - due).days
            except (ValueError, TypeError):
                dpd = 0
            if dpd < 0:
                b = "Not Yet Due"
            elif dpd <= 30:
                b = "0-30"
            elif dpd <= 60:
                b = "31-60"
            elif dpd <= 90:
                b = "61-90"
            elif dpd <= 120:
                b = "91-120"
            else:
                b = "120+"
            bucket_totals[b] += ad
            bucket_counts[b] += 1
    if dates:
        print(f"  date range: {min(dates)}  ->  {max(dates)}")
    print(f"  statuses: {dict(statuses)}")
    print(f"  sum(AmountDue) all rows: {total_due:,.2f}")
    print(f"  open (AmountDue>0 & not paid/void): {open_count} invoices, {open_due:,.2f}")
    if bucket_totals:
        print("  bucket breakdown of open AR:")
        for b in ["Not Yet Due", "0-30", "31-60", "61-90", "91-120", "120+"]:
            if bucket_counts[b]:
                print(f"    {b:12s}  {bucket_counts[b]:5d} inv  {bucket_totals[b]:>14,.2f}")


inv, _ = fetch_all('where=Type=="ACCREC"&Statuses=AUTHORISED,SUBMITTED&summaryOnly=true')
summarize("ACCREC + Statuses(AUTHORISED,SUBMITTED) + summaryOnly", inv)
