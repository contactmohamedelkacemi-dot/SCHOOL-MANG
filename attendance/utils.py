from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from .models import AttendanceSession, StudentRisk, Notification

def get_student_analytics(student):
    """
    Returns total, present, absent, late, absence_rate, and recent_absence_rate for a student.
    """
    seven_days_ago = timezone.now().date() - timedelta(days=7)
    
    stats = AttendanceSession.objects.filter(student=student).aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='Present')),
        absent=Count('id', filter=Q(status='Absent')),
        late=Count('id', filter=Q(status='Late')),
        recent_total=Count('id', filter=Q(date__gte=seven_days_ago)),
        recent_absent=Count('id', filter=Q(status='Absent', date__gte=seven_days_ago))
    )
    
    total = stats['total'] or 0
    present = stats['present'] or 0
    absent = stats['absent'] or 0
    late = stats['late'] or 0
    recent_total = stats['recent_total'] or 0
    
    attendance_rate = (round(((present + late) / total) * 100, 1)) if total > 0 else 0
    absence_rate = (absent / total * 100) if total > 0 else 0
    late_rate = (late / total * 100) if total > 0 else 0
    recent_absence_rate = (stats['recent_absent'] / recent_total * 100) if recent_total > 0 else absence_rate
    
    return {
        'total': total,
        'present': present,
        'absent': absent,
        'late': late,
        'attendance_rate': attendance_rate,
        'absence_rate': absence_rate,
        'late_rate': late_rate,
        'recent_absence_rate': recent_absence_rate,
        'recent_total': recent_total,
    }

def calculate_student_risk(student):
    """
    Calculates the predictive risk score for a student.
    Returns: risk_score, risk_level, trend_direction ('up', 'down', 'stable')
    """
    stats = get_student_analytics(student)
    
    if stats['total'] < 10:
        return 0.0, 'Safe', 'stable', stats
        
    # Formula: risk_score = (absence_rate * 0.6) + (recent_trend * 0.3) + (late_rate * 0.1)
    risk_score = (stats['absence_rate'] * 0.6) + (stats['recent_absence_rate'] * 0.3) + (stats['late_rate'] * 0.1)
    risk_score = min(round(risk_score, 1), 100.0)
    
    if risk_score > 70:
        risk_level = 'Critical'
    elif risk_score > 40:
        risk_level = 'At Risk'
    else:
        risk_level = 'Safe'
        
    trend_direction = 'stable'
    # If recent absence rate is higher than overall absence rate by at least 10%, attendance is dropping (risk going UP)
    if stats['recent_absence_rate'] > stats['absence_rate'] + 10:
        trend_direction = 'down' # Attendance dropping -> Risk goes up (we'll show a red down arrow for attendance)
    elif stats['recent_absence_rate'] < stats['absence_rate'] - 10:
        trend_direction = 'up' # Attendance improving -> Risk goes down
        
    return risk_score, risk_level, trend_direction, stats

def check_consecutive_absences(student):
    """
    Checks if the student's last 3 recorded sessions are all 'Absent'.
    """
    recent_sessions = AttendanceSession.objects.filter(student=student).order_by('-date', '-session_number')[:3]
    if len(recent_sessions) == 3 and all(s.status == 'Absent' for s in recent_sessions):
        return True
    return False

def update_student_risk(student):
    """
    Main service function called after attendance is saved.
    Updates the StudentRisk profile and triggers notifications if the level changed.
    """
    risk_score, risk_level, trend_direction, stats = calculate_student_risk(student)
    
    if stats['total'] < 10:
        return # Not enough data
        
    risk_profile, created = StudentRisk.objects.get_or_create(
        student=student, 
        defaults={'risk_score': risk_score, 'risk_level': risk_level}
    )
    
    old_level = risk_profile.risk_level
    
    if not created and old_level != risk_level:
        # Risk level changed! Trigger Notification
        message = f"Risk level changed from {old_level} to {risk_level}. Current score: {risk_score}."
        Notification.objects.create(
            student=student,
            type='RISK_LEVEL_CHANGE',
            message=message
        )
        
        # Skeleton for email notification
        _send_risk_email_skeleton(student, risk_level, message)
        
    # Update profile
    risk_profile.risk_score = risk_score
    risk_profile.risk_level = risk_level
    risk_profile.save()
    
    # Check for consecutive absences
    if check_consecutive_absences(student):
        # Prevent spam by checking if we recently notified about consecutive absences
        # E.g. check if there's a notification today
        today = timezone.now().date()
        recent_notif = Notification.objects.filter(
            student=student, 
            type='CONSECUTIVE_ABSENCES', 
            created_at__date=today
        ).exists()
        
        if not recent_notif:
            Notification.objects.create(
                student=student,
                type='CONSECUTIVE_ABSENCES',
                message="Student has missed 3 consecutive sessions."
            )

def _send_risk_email_skeleton(student, risk_level, message):
    """
    Prepares structure for email notifications.
    TODO: Implement SMTP logic.
    """
    # print(f"EMAIL NOTIFICATION SKELETON Triggered:")
    # print(f"To: admin@example.com, parent of {student}")
    # print(f"Subject: Urgent: {student.full_name} Attendance Alert - {risk_level}")
    # print(f"Body: {message}")
    pass
