from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from xero_app.mailer import send_app_email

from .decorators import super_admin_required
from .forms import (AdminSetPasswordForm, UserCreateForm, UserEditForm,
                    UserInviteForm)
from .models import Role, User
from .tokens import invite_token_generator


# ---------------------------------------------------------------------------
# Invite helpers
# ---------------------------------------------------------------------------

def _send_invite(user):
    """Email a fresh set-password/activation link to an (inactive) user.
    Returns True if the message was sent."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = invite_token_generator.make_token(user)
    link = settings.SITE_BASE_URL + reverse(
        'accept_invite', kwargs={'uidb64': uid, 'token': token})
    days = max(1, settings.PASSWORD_RESET_TIMEOUT // 86400)
    plural = '' if days == 1 else 's'
    name = user.get_full_name() or user.email
    role = user.get_role_display()

    text = (
        f"Hi {name},\n\n"
        f"You've been invited to the FSA Debtor System as {role}.\n\n"
        f"Set your password and activate your account here:\n{link}\n\n"
        f"This link expires in {days} day{plural}. "
        f"If you weren't expecting this, you can ignore this email.\n"
    )
    html = (
        f"<p>Hi {name},</p>"
        f"<p>You've been invited to the <strong>FSA Debtor System</strong> "
        f"as <strong>{role}</strong>.</p>"
        f'<p><a href="{link}" style="display:inline-block;padding:10px 18px;'
        f'background:#0E7C7B;color:#fff;text-decoration:none;border-radius:6px;'
        f'font-weight:600;">Set your password</a></p>'
        f'<p>Or paste this link into your browser:<br>'
        f'<a href="{link}">{link}</a></p>'
        f'<p style="color:#888;font-size:13px;">This link expires in {days} '
        f"day{plural}. If you weren't expecting this, ignore this email.</p>"
    )
    try:
        return bool(send_app_email(
            subject="You're invited to the FSA Debtor System",
            body=text, to=user.email, html_body=html,
        ))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@super_admin_required
def user_list(request):
    search = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    users = User.objects.all()
    if search:
        users = users.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )
    if role:
        users = users.filter(role=role)
    return render(request, 'accounts/user_list.html', {
        'users': users,
        'search': search,
        'role_filter': role,
        'roles': Role.choices,
    })


@super_admin_required
def user_invite(request):
    """Create a pending user and email them an invite link. The role is chosen
    here, before the invite goes out."""
    if request.method == 'POST':
        form = UserInviteForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.set_unusable_password()
            user.save()
            if _send_invite(user):
                messages.success(request, f'Invite sent to {user.email}.')
            else:
                messages.warning(
                    request,
                    f'{user.email} was created but the invite email could not be '
                    f'sent. Use "Resend invite" to try again.',
                )
            return redirect('user_list')
    else:
        form = UserInviteForm()
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Invite User',
        'submit_label': 'Send Invite',
    })


@super_admin_required
def user_resend_invite(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if not target.is_pending_invite:
            messages.error(request, f'{target.email} has already activated their account.')
        elif _send_invite(target):
            messages.success(request, f'Invite re-sent to {target.email}.')
        else:
            messages.error(request, f'Could not send the invite to {target.email}.')
    return redirect('user_list')


def accept_invite(request, uidb64, token):
    """Public page: an invited user sets their password and activates the
    account, then is signed in."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not invite_token_generator.check_token(user, token):
        return render(request, 'accounts/accept_invite.html', {'invalid': True})

    if request.method == 'POST':
        form = AdminSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()                       # sets and saves the new password
            user.is_active = True
            user.save(update_fields=['is_active'])
            login(request, user)
            messages.success(request, 'Welcome! Your account is now active.')
            return redirect('home')
    else:
        form = AdminSetPasswordForm(user)
    return render(request, 'accounts/accept_invite.html', {
        'form': form, 'invited_user': user,
    })


@super_admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.email} created.')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Add User',
        'submit_label': 'Create User',
    })


@super_admin_required
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {target.email} updated.')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=target)
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f'Edit {target.get_full_name() or target.email}',
        'submit_label': 'Save Changes',
        'target': target,
    })


@super_admin_required
def user_reset_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminSetPasswordForm(target, request.POST)
        if form.is_valid():
            form.save()
            if target == request.user:
                update_session_auth_hash(request, target)
            messages.success(request, f'Password reset for {target.email}.')
            return redirect('user_list')
    else:
        form = AdminSetPasswordForm(target)
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f'Reset password - {target.get_full_name() or target.email}',
        'submit_label': 'Set Password',
        'target': target,
    })


@super_admin_required
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if target == request.user:
            messages.error(request, "You can't deactivate your own account.")
        else:
            target.is_active = not target.is_active
            target.save(update_fields=['is_active'])
            state = 'activated' if target.is_active else 'deactivated'
            messages.success(request, f'{target.email} {state}.')
    return redirect('user_list')


@super_admin_required
def user_delete(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if target == request.user:
            messages.error(request, "You can't delete your own account.")
        else:
            email = target.email
            target.delete()
            messages.success(request, f'User {email} deleted.')
    return redirect('user_list')
