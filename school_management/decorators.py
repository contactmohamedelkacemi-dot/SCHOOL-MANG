from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def is_teacher(user):
    return user.is_authenticated and user.role == 'formateur'

def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is an admin,
    raising PermissionDenied if not.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not user_passes_test(is_admin)(view_func):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return user_passes_test(is_admin, login_url='/accounts/login/')(view_func)

def teacher_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a teacher,
    raising PermissionDenied if not.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not user_passes_test(is_teacher)(view_func):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return user_passes_test(is_teacher, login_url='/accounts/login/')(view_func)
