"""Quick verification: bucket breakdown straight from the OpenInvoiceSnapshot table."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.db.models import Sum, Count, Min, Max
from xero_app.models import OpenInvoiceSnapshot, SyncRun, XeroConnection

conn = XeroConnection.objects.first()
print(f"Tenant: {conn.tenant_name}")

agg = OpenInvoiceSnapshot.objects.filter(tenant_id=conn.tenant_id).aggregate(
    total=Sum("amount_due"),
    count=Count("id"),
    earliest=Min("invoice_date"),
    latest=Max("invoice_date"),
)
print(f"\nTotal open invoices: {agg['count']}")
print(f"Total outstanding:   {agg['total']:,.2f}")
print(f"Invoice date range:  {agg['earliest']}  ->  {agg['latest']}")

print("\nBy bucket:")
for row in (
    OpenInvoiceSnapshot.objects
    .filter(tenant_id=conn.tenant_id)
    .values("bucket")
    .annotate(amount=Sum("amount_due"), n=Count("id"))
    .order_by("bucket")
):
    print(f"  {row['bucket']:12s}  {row['n']:5d} inv  {row['amount']:>16,.2f}")

print("\nTop 10 debtors by outstanding:")
for row in (
    OpenInvoiceSnapshot.objects
    .filter(tenant_id=conn.tenant_id)
    .values("contact_name")
    .annotate(amount=Sum("amount_due"), n=Count("id"))
    .order_by("-amount")[:10]
):
    print(f"  {row['amount']:>14,.2f}  ({row['n']:4d} inv)  {row['contact_name']}")

last = SyncRun.objects.first()
print(f"\nLast sync: {last.status}  finished {last.finished_at}  invoices={last.invoice_count}")
