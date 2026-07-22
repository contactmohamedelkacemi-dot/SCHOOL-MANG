"""
Permission helpers for the communication system.
Centralises role-based access checks so views stay clean.
"""

from django.db.models import Q
from classes.models import Group


def get_allowed_contacts(user):
    """
    Return a queryset of User objects that *user* is allowed to message.
    Rules:
      - Admin  → everyone
      - Teacher → their assigned students + all admins
      - Student → their assigned teachers + all admins
    """
    from accounts.models import User  # late import to avoid circular

    if user.role == 'admin':
        return User.objects.exclude(pk=user.pk).filter(
            role__in=['admin', 'formateur', 'stagiaire']
        )

    if user.role == 'formateur':
        # Groups this teacher belongs to
        try:
            teacher = user.teacher
        except Exception:
            return User.objects.none()

        student_user_ids = (
            Group.objects.filter(teachers=teacher)
            .values_list('students__user__pk', flat=True)
        )
        admin_ids = User.objects.filter(role='admin').values_list('pk', flat=True)
        return User.objects.filter(
            Q(pk__in=student_user_ids) | Q(pk__in=admin_ids)
        ).exclude(pk=user.pk).distinct()

    if user.role == 'stagiaire':
        try:
            student = user.student
        except Exception:
            return User.objects.none()

        teacher_user_ids = (
            Group.objects.filter(students=student)
            .values_list('teachers__user__pk', flat=True)
        )
        admin_ids = User.objects.filter(role='admin').values_list('pk', flat=True)
        return User.objects.filter(
            Q(pk__in=teacher_user_ids) | Q(pk__in=admin_ids)
        ).exclude(pk=user.pk).distinct()

    return User.objects.none()


def can_message(sender, receiver):
    """Return True if sender is allowed to send a message to receiver."""
    return get_allowed_contacts(sender).filter(pk=receiver.pk).exists()


def can_access_group_chat(user, group):
    """
    Return True if *user* may participate in this Group's chat.
    Rules: admin=always, teacher=in group's teachers, student=in group's students.
    """
    if user.role == 'admin':
        return True

    if user.role == 'formateur':
        try:
            return group.teachers.filter(pk=user.teacher.pk).exists()
        except Exception:
            return False

    if user.role == 'stagiaire':
        try:
            return group.students.filter(pk=user.student.pk).exists()
        except Exception:
            return False

    return False
