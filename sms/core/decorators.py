from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Allow only the listed roles. Super Admin is also allowed wherever Admin is."""
    allowed = set(roles)
    if "admin" in allowed:
        allowed.add("superadmin")

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator
