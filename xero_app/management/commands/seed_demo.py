"""Seed demo data for showcasing the app (no live Xero needed).

Populates:
  * Reflected Xero reminder history per invoice (following the 7-stage cadence).
  * Dummy contact details for every company.
  * Comet Abattoir as a troublesome customer (rich reminder trail + collection notes).

Re-runnable: it replaces previously seeded reminder history / contact details.
Run:  python manage.py seed_demo
"""
import json
import random
from datetime import datetime, timedelta, timezone as dttz

from django.core.management.base import BaseCommand
from django.utils import timezone

from xero_app.models import (XeroConnection, OpenInvoiceSnapshot, InvoiceHistory,
                             ContactDetail, InvoiceComment, DebtorAllocation)
from xero_app.outreach import OUTREACH_STAGES

STREETS = ["Main Rd", "Voortrekker St", "Church St", "Market St", "Industria Ave",
           "Mill St", "Station Rd", "Long St", "Plein St", "Andries St"]
CITIES = [("Johannesburg", "Gauteng", "2001", "11"), ("Cape Town", "Western Cape", "8001", "21"),
          ("Durban", "KwaZulu-Natal", "4001", "31"), ("Pretoria", "Gauteng", "0002", "12"),
          ("Bloemfontein", "Free State", "9301", "51"), ("Gqeberha", "Eastern Cape", "6001", "41"),
          ("Polokwane", "Limpopo", "0700", "15"), ("Mbombela", "Mpumalanga", "1200", "13")]
FIRST = ["Johan", "Thabo", "Sarah", "Nomsa", "Pieter", "Lerato", "David", "Anele", "Riaan", "Zanele"]
LAST = ["van der Merwe", "Nkosi", "Botha", "Dlamini", "Pretorius", "Mokoena", "Smith", "Khumalo", "Naidoo", "Jacobs"]

# A troublesome-customer collection script (relative day offset from due date, note).
COMET_NOTES = [
    (2, "Emailed statement and copy invoice to accounts dept. No acknowledgement."),
    (9, "Called accounts — switchboard took a message, no call back."),
    (16, "Spoke to Mr Coetzee (Accounts). Promised payment by month-end."),
    (24, "Promised payment date passed. No payment received, no communication."),
    (33, "Second call — now disputes a portion of the invoice. Asked for breakdown (already sent twice)."),
    (47, "Third broken promise to pay. Advised final demand will follow."),
    (62, "Final demand acknowledged via email but no payment. Stalling."),
    (68, "No response to handover warning. Recommend escalation to legal / handover process."),
]


class Command(BaseCommand):
    help = "Seed demo reminder history, contact details, and a troublesome customer."

    def handle(self, *args, **opts):
        conn = XeroConnection.objects.first()
        if not conn:
            self.stderr.write("No XeroConnection — nothing to seed.")
            return
        tid = conn.tenant_id
        today = timezone.now().date()

        snaps = list(OpenInvoiceSnapshot.objects.filter(tenant_id=tid).values(
            "contact_id", "contact_name", "contact_email", "invoice_id",
            "invoice_number", "invoice_date", "due_date", "days_past_due"))

        self._seed_reminders(tid, snaps)
        self._seed_contacts(tid, snaps)
        self._seed_comet(tid, snaps)

    # ---- reminder history per invoice (reflected from Xero cadence) ----
    def _seed_reminders(self, tid, snaps):
        InvoiceHistory.objects.filter(tenant_id=tid).delete()
        rows = []
        for s in snaps:
            email = s["contact_email"] or "accounts@" + _slug(s["contact_name"]) + ".co.za"
            events = []
            if s["invoice_date"]:
                events.append(_ev(s["invoice_date"], "Sent", f"Invoice {s['invoice_number']} emailed to {email}", True))
            dpd = s["days_past_due"]
            if s["due_date"] is not None:
                for label, offset, _call in OUTREACH_STAGES:
                    if dpd is not None and dpd >= offset:
                        d = s["due_date"] + timedelta(days=offset)
                        events.append(_ev(d, label, f"Reminder emailed to {email}", True))
            events.sort(key=lambda e: e["date"])
            rows.append(InvoiceHistory(tenant_id=tid, invoice_id=s["invoice_id"],
                                       events_json=json.dumps(events)))
        InvoiceHistory.objects.bulk_create(rows, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Seeded reminder history for {len(rows)} invoices."))

    # ---- dummy contact details for every company ----
    def _seed_contacts(self, tid, snaps):
        ContactDetail.objects.filter(tenant_id=tid).delete()
        seen = {}
        for s in snaps:
            cid = s["contact_id"] or s["contact_name"] or "Unknown"
            if cid in seen:
                continue
            seen[cid] = self._dummy_contact(s["contact_name"] or "Unknown", s["contact_email"] or "")
        rows = [ContactDetail(tenant_id=tid, contact_id=cid, data_json=json.dumps(data))
                for cid, data in seen.items()]
        ContactDetail.objects.bulk_create(rows, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Seeded contact details for {len(rows)} companies."))

    def _dummy_contact(self, name, email):
        rng = random.Random(name)
        city, region, postal, area = rng.choice(CITIES)
        street = f"{rng.randint(1, 240)} {rng.choice(STREETS)}"
        person = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        digits = "".join(str(rng.randint(0, 9)) for _ in range(7))
        return {
            "name": name,
            "account_number": f"FSA-{rng.randint(1000, 9999)}",
            "email": email or "accounts@" + _slug(name) + ".co.za",
            "status": "ACTIVE",
            "tax_number": f"4{rng.randint(100000000, 999999999)}",
            "default_currency": "ZAR",
            "phones": [
                {"type": "Default", "number": f"+27 {area} {digits[:3]} {digits[3:]}"},
                {"type": "Mobile", "number": f"+27 8{rng.randint(0,3)} {digits[:3]} {digits[3:]}"},
            ],
            "addresses": [{"type": "Street", "lines": [street, f"{city}, {region}, {postal}", "South Africa"]}],
            "contact_persons": [{"name": person, "email": "accounts@" + _slug(name) + ".co.za"}],
            "payment_terms": "30 days after invoice date",
        }

    # ---- Comet Abattoir: troublesome customer ----
    def _seed_comet(self, tid, snaps):
        comet = [s for s in snaps if "comet" in (s["contact_name"] or "").lower()]
        if not comet:
            self.stdout.write("No Comet Abattoir invoices found — skipping troublesome seed.")
            return
        invoice_ids = [s["invoice_id"] for s in comet]
        InvoiceComment.objects.filter(tenant_id=tid, invoice_id__in=invoice_ids).delete()

        cid = comet[0]["contact_id"] or comet[0]["contact_name"]
        alloc = DebtorAllocation.objects.filter(tenant_id=tid, contact_id=cid).select_related("administrator").first()
        author = alloc.administrator if alloc else None
        author_name = (author.get_full_name() or author.email) if author else "Collections"

        # Concentrate the collection trail on Comet's most-overdue invoice.
        target = max(comet, key=lambda s: s["days_past_due"] or 0)
        due = target["due_date"] or (timezone.now().date() - timedelta(days=70))
        made = 0
        for offset, note in COMET_NOTES:
            cdate = due + timedelta(days=offset)
            if cdate > timezone.now().date():
                continue
            dt = timezone.make_aware(datetime(cdate.year, cdate.month, cdate.day, 11, 0), dttz.utc)
            InvoiceComment.objects.create(
                tenant_id=tid, invoice_id=target["invoice_id"], author=author,
                author_name=author_name, comment_at=dt, text=note)
            made += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {made} collection notes on Comet Abattoir invoice {target['invoice_number']}."))


def _ev(d, action, details, is_email):
    return {"date": d.strftime("%Y-%m-%d 09:00"), "user": "Xero", "action": action,
            "details": details, "is_email": is_email}


def _slug(name):
    return "".join(c.lower() if c.isalnum() else "" for c in (name or "company"))[:24] or "company"
