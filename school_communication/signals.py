"""
Signal handlers for auto-notifications.
Triggers notifications when reports/justifications are created or updated.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='students.Report')
def notify_on_report(sender, instance, created, **kwargs):
    """Notify admin when a new report is submitted or flagged as high priority."""
    from .models import SmartNotification
    from accounts.models import User

    if created:
        # Notify all admins
        admins = User.objects.filter(role='admin')
        for admin in admins:
            notif_type = 'critical' if instance.priority == 'High' else 'info'
            SmartNotification.objects.create(
                recipient=admin,
                notif_type=notif_type,
                category='report' if instance.priority != 'High' else 'report_priority',
                title=f'New Report: {instance.title}',
                message=f'{instance.teacher.full_name} submitted a report about {instance.student.full_name}',
                url=f'/students/reports/admin/',
            )
    else:
        # Check if priority was changed to High
        if instance.priority == 'High' and instance.is_flagged:
            admins = User.objects.filter(role='admin')
            for admin in admins:
                SmartNotification.objects.create(
                    recipient=admin,
                    notif_type='critical',
                    category='report_priority',
                    title=f'⚠ High Priority Report: {instance.title}',
                    message=f'Report about {instance.student.full_name} has been flagged',
                    url=f'/students/reports/admin/',
                )


@receiver(post_save, sender='attendance.Justification')
def notify_on_justification(sender, instance, created, **kwargs):
    """Notify admin when a justification is submitted."""
    from .models import SmartNotification
    from accounts.models import User

    if created:
        admins = User.objects.filter(role='admin')
        for admin in admins:
            SmartNotification.objects.create(
                recipient=admin,
                notif_type='info',
                category='justification',
                title='New Justification Submitted',
                message=f'{instance.student.full_name} submitted a justification for {instance.date}',
                url=f'/attendance/justifications/',
            )
    elif instance.status == 'Pending':
        admins = User.objects.filter(role='admin')
        for admin in admins:
            SmartNotification.objects.create(
                recipient=admin,
                notif_type='warning',
                category='justification_pending',
                title='Justification Pending Validation',
                message=f'Justification from {instance.student.full_name} needs review',
                url=f'/attendance/justifications/',
            )
