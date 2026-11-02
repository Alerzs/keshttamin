from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if user.status != user.Status.ACTIVE or user.role not in roles:
                return redirect('home')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


investor_required = role_required('investor')
staff_required = role_required('admin', 'operator')
admin_required = role_required('admin')
