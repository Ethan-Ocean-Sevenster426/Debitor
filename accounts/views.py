from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import super_admin_required
from .forms import AdminSetPasswordForm, UserCreateForm, UserEditForm
from .models import User


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
