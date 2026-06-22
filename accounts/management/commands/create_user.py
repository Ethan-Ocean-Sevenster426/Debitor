"""Create (or update) a login for any of the three roles.

One command covers every role — pass ``--role super_admin|administrator|lawyer``:

    python manage.py create_user boss@example.com   --role super_admin   --first-name Boss   --last-name One
    python manage.py create_user clerk@example.com  --role administrator --first-name Clerk  --last-name Two
    python manage.py create_user counsel@example.com --role lawyer        --first-name Counsel --last-name Three

Notes:
* ``super_admin`` also gets ``is_staff``/``is_superuser`` (Django /admin access),
  matching how ``createsuperuser`` behaves. ``administrator`` and ``lawyer`` get
  app access via their role only.
* All created users are ``is_active=True`` and can log in immediately (this bypasses
  the email-invite flow — use *Users -> Invite User* in the app for self-service).
* Omit ``--password`` to have a strong one generated and printed once.
* Pass ``--update`` to modify an existing user (role / name / password) instead of erroring.
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = "Create or update a user with a given role (super_admin, administrator, lawyer)."

    def add_arguments(self, parser):
        parser.add_argument("email", help="The user's email address (used as the login).")
        parser.add_argument(
            "--role", required=True, choices=list(Role.values),
            help="super_admin | administrator | lawyer",
        )
        parser.add_argument(
            "--password", default=None,
            help="Password to set. If omitted, a strong random one is generated and printed.",
        )
        parser.add_argument("--first-name", dest="first_name", default="")
        parser.add_argument("--last-name", dest="last_name", default="")
        parser.add_argument(
            "--update", action="store_true",
            help="Update the user if it already exists instead of failing.",
        )

    @staticmethod
    def _generate_password(length=14):
        alphabet = string.ascii_letters + string.digits + "!@#$%*?"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def handle(self, *args, **opts):
        email = User.objects.normalize_email(opts["email"]).strip()
        if not email:
            raise CommandError("An email address is required.")

        role = opts["role"]
        is_admin_role = role == Role.SUPER_ADMIN

        existing = User.objects.filter(email__iexact=email).first()
        if existing and not opts["update"]:
            raise CommandError(
                f"User {existing.email} already exists (role={existing.role or 'none'}). "
                f"Pass --update to modify it."
            )

        # Decide the password: provided wins; otherwise generate for a NEW user, or
        # leave an existing user's password untouched on --update.
        password = opts["password"]
        generated = False
        if password is None and existing is None:
            password = self._generate_password()
            generated = True

        if existing:
            user = existing
            user.role = role
            if opts["first_name"]:
                user.first_name = opts["first_name"]
            if opts["last_name"]:
                user.last_name = opts["last_name"]
            user.is_active = True
            user.is_staff = is_admin_role
            user.is_superuser = is_admin_role
            if password is not None:
                user.set_password(password)
            user.save()
            action = "Updated"
        elif is_admin_role:
            user = User.objects.create_superuser(
                email, password,
                first_name=opts["first_name"], last_name=opts["last_name"],
            )
            action = "Created"
        else:
            user = User.objects.create_user(
                email, password, role=role, is_active=True,
                first_name=opts["first_name"], last_name=opts["last_name"],
            )
            action = "Created"

        self.stdout.write(self.style.SUCCESS(
            f"{action} {user.email}  |  role={user.role}  |  "
            f"staff={user.is_staff}  active={user.is_active}"
        ))
        if generated:
            self.stdout.write(self.style.WARNING(
                f"Generated password (shown once): {password}"
            ))
        elif password is not None:
            self.stdout.write("Password set from --password.")
        else:
            self.stdout.write("Password left unchanged.")
