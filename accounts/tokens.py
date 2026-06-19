"""Token generator for user-invite links.

Subclasses Django's password-reset token generator, so each link's hash already
folds in the user's password + last_login + email — which makes the link
single-use: once the invitee sets a password (and we activate the account) the
token no longer validates. A distinct salt keeps invite links and password-reset
links from being interchangeable. Expiry uses settings.PASSWORD_RESET_TIMEOUT.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class InviteTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "accounts.tokens.InviteTokenGenerator"


invite_token_generator = InviteTokenGenerator()
