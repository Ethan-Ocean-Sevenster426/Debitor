"""Send the weekly lawyer progress report — if it's due.

Designed to be run frequently by the Windows Scheduled Task (alongside, or like,
sync_xero). The schedule lives in the database (LawyerReportConfig); this command
just asks `is_due()` and sends when the configured slot arrives, so the schedule
is fully managed from the UI.

    python manage.py send_lawyer_report            # send only if due
    python manage.py send_lawyer_report --force    # send right now
    python manage.py send_lawyer_report --to me@x  # test send to one address only
"""
from django.core.management.base import BaseCommand

from xero_app import reports
from xero_app.models import LawyerReportConfig, ReportRecipient, XeroConnection


class Command(BaseCommand):
    help = "Send the weekly lawyer progress report when it is due (or with --force)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Send now, ignoring the configured schedule.")
        parser.add_argument("--to", help="Send only to this address (for testing). "
                                         "Does not update the last-sent time.")

    def handle(self, *args, **options):
        conn = XeroConnection.objects.first()
        if not conn:
            self.stdout.write("No Xero connection on record — cannot determine tenant.")
            return
        tenant_id = conn.tenant_id

        cfg = LawyerReportConfig.get_solo()
        force = options["force"]
        test_to = options.get("to")

        if not force and not test_to and not cfg.is_due():
            self.stdout.write("Lawyer report not due yet — skipping. (use --force to send now)")
            return

        if test_to:
            recipients = [test_to]
        else:
            recipients = list(ReportRecipient.objects.filter(is_active=True)
                              .values_list("email", flat=True))
            if not recipients:
                self.stdout.write("No active report recipients configured — nothing to send.")
                return

        sent, ctx = reports.send_lawyer_report(
            tenant_id, recipients=recipients, mark_sent=not test_to)
        k = ctx["kpis"]
        if sent:
            self.stdout.write(self.style.SUCCESS(
                f"Lawyer report sent to {len(recipients)} recipient(s): "
                f"{k['new']} new, {k['active']} active, {k['idle_14']} idle 14+ days."))
        else:
            self.stdout.write(self.style.WARNING("Report was not sent — check email configuration."))
