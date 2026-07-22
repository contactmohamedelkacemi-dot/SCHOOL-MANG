from django.shortcuts import redirect

def home_redirect(request):
    """
    Root URL dispatcher.
    Redirects unauthenticated users to login.
    Redirects authenticated users to their specific role-based dashboard.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
        
    if request.user.role == 'admin':
        return redirect('dashboard:admin_dashboard')
    elif request.user.role == 'formateur':
        return redirect('dashboard:teacher_dashboard')
    elif request.user.role == 'stagiaire':
        return redirect('dashboard:student_dashboard')
        
    # Fallback
    return redirect('accounts:login')
