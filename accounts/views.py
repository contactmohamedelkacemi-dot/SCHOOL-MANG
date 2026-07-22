from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse
import secrets
import string
from django.views.decorators.http import require_POST
from school_management.decorators import admin_required
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            login(request, user)
            return redirect_based_on_role(user)
        else:
            messages.error(request, "Invalid username or password")
            form = AuthenticationForm()
    else:
        # Check for password reset success parameter
        if request.GET.get('reset') == 'success':
            messages.success(request, 'Password reset complete! You may now log in.')
            
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect("accounts:login")


@login_required
def force_password_change(request):
    if not getattr(request.user, "must_change_password", False):
        return redirect("dashboard:index")

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update session to prevent logging out
            update_session_auth_hash(request, user)

            user.must_change_password = False
            user.save()

            messages.success(request, "Your password was successfully updated!")
            return redirect("dashboard:index")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "accounts/force_password_change.html", {"form": form})


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            if getattr(user, "must_change_password", False):
                user.must_change_password = False
                user.save()

            messages.success(request, "Your password was successfully updated!")
            return redirect("dashboard:index")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "accounts/password_change.html", {"form": form})


def redirect_based_on_role(user):
    # Force password change if required
    if getattr(user, 'must_change_password', False):
        return redirect('accounts:force_password_change')
        
    if user.role == "admin":
        return redirect("dashboard:admin_dashboard")
    elif user.role == "formateur":
        return redirect("dashboard:teacher_dashboard")
    elif user.role == "stagiaire":
        return redirect("dashboard:student_dashboard")
    else:
        # Fallback if no valid role
        return redirect("accounts:login")


@require_POST
@admin_required
def admin_reset_password(request, user_id):
    """
    Allows an admin to randomly generate a new password for a user,
    force them to change it on next login, and return the new plain text password.
    """
    try:
        user = User.objects.get(id=user_id)

        # Don't allow resetting other admins for security
        if user.role == "admin":
            return JsonResponse({"error": "Cannot reset admin passwords."}, status=403)

        # Generate an 8-character secure random password
        alphabet = string.ascii_letters + string.digits
        new_password = "".join(secrets.choice(alphabet) for i in range(8))

        # Save password securely using Django's hashing
        user.set_password(new_password)
        user.must_change_password = True
        user.save()

        return JsonResponse(
            {"success": True, "password": new_password, "username": user.username}
        )
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
