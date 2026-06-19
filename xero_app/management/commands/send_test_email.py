"""Send a test email to confirm the system mailbox / SMTP settings work.

Usage:
    python manage.py send_test_email you@example.com

Prints the active backend and sender so you can see at a glance whether real
SMTP is wired up or the console fallback is in effect.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from xero_app.mailer import send_app_email


class Command(BaseCommand):
    help = "Send a test email to confirm the mailbox / SMTP settings work."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Email address to send the test message to.")

    def handle(self, *args, **options):
        to = options["recipient"]
        live = getattr(settings, "EMAIL_ENABLED", False)

        self.stdout.write("FSA Debtor System — email configuration")
        self.stdout.write(f"  Backend : {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  Sender  : {settings.MS_GRAPH_SENDER or '(not set)'}")
        self.stdout.write(f"  Graph configured: {'YES' if live else 'NO — set the MS_GRAPH_* values in .env'}")
        self.stdout.write(f"Sending test message to {to} ...")

        try:
            sent = send_app_email(
                subject="FSA Debtor System — test email",
                body=(
                    "This is a test message from the FSA Debtor System.\n\n"
                    "If you are reading this in your inbox, outbound email is "
                    "configured correctly and the system can send mail.\n"
                ),
                to=to,
            )
        except Exception as exc:  # surface the real Graph error to the operator
            raise CommandError(f"Send failed: {exc}")

        if sent:
            self.stdout.write(self.style.SUCCESS(f"OK — test email sent to {to} via Microsoft Graph."))
        else:
            self.stdout.write(self.style.WARNING(
                "No message was sent. Check that the MS_GRAPH_* values are set in .env "
                "and the app registration has admin-consented Mail.Send permission."
            ))
