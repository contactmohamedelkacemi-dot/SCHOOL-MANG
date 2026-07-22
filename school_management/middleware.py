from django.shortcuts import redirect
from django.urls import reverse

class ProfileCompletionMiddleware:
    """
    Middleware that forces users to complete their profile or change their password
    if required.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Paths that are allowed even if profile/password is pending
            allowed_paths = [
                reverse('dashboard:complete_profile'),
                reverse('accounts:force_password_change'),
                reverse('accounts:logout'),
            ]
            
            if request.path not in allowed_paths and not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                if getattr(request.user, 'must_change_password', False):
                    return redirect('accounts:force_password_change')
                if getattr(request.user, 'is_profile_complete', False) == False:
                    return redirect('dashboard:complete_profile')

        response = self.get_response(request)
        return response
