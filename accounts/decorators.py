from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Allow only authenticated users whose role is in `roles`.

    Super Admins always pass, since they have full access by design.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.is_super_admin or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped

    return decorator


def super_admin_required(view_func):
    """Allow only Super Admins."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_super_admin:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped
