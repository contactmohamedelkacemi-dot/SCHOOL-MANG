import csv
from django.http import HttpResponse
from .models import AttendanceSession, Justification

def generate_attendance_csv(queryset, filename="attendance_report.csv"):
    """
    Generate a CSV from an AttendanceSession queryset grouped by student and date.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Group', 'Date', 'Session 1', 'Session 2', 'Session 3', 'Session 4', 'Daily Status', 'Justification'])

    # Group sessions by student and date
    # Pre-fetch justifications to avoid N+1
    student_ids = queryset.values_list('student_id', flat=True).distinct()
    dates = queryset.values_list('date', flat=True).distinct()
    
    justifications = Justification.objects.filter(student_id__in=student_ids, date__in=dates)
    justif_map = {(j.student_id, j.date): j for j in justifications}
    
    # Process queryset and group by (student, date)
    daily_records = {}
    for session in queryset.select_related('student', 'group').order_by('date', 'student__full_name'):
        key = (session.student_id, session.date)
        if key not in daily_records:
            daily_records[key] = {
                'student': session.student.full_name,
                'group': session.group.name,
                'date': session.date,
                'sessions': {1: '-', 2: '-', 3: '-', 4: '-'}
            }
        daily_records[key]['sessions'][session.session_number] = session.status
        
    for key, record in daily_records.items():
        s_vals = list(record['sessions'].values())
        
        # Calculate daily status
        if 'Absent' in s_vals:
            daily_status = 'Absent'
        elif 'Late' in s_vals:
            daily_status = 'Late'
        elif 'Present' in s_vals:
            daily_status = 'Present'
        else:
            daily_status = '-'
            
        justif_status = '-'
        if daily_status == 'Absent':
            justif = justif_map.get(key)
            if justif:
                justif_status = justif.status
            else:
                justif_status = 'Non justifié'
                
        writer.writerow([
            record['student'],
            record['group'],
            record['date'],
            record['sessions'].get(1, '-'),
            record['sessions'].get(2, '-'),
            record['sessions'].get(3, '-'),
            record['sessions'].get(4, '-'),
            daily_status,
            justif_status
        ])
        
    return response

def get_attendance_report_data(queryset):
    """
    Returns structured data for the HTML report view.
    """
    student_ids = queryset.values_list('student_id', flat=True).distinct()
    dates = queryset.values_list('date', flat=True).distinct()
    
    justifications = Justification.objects.filter(student_id__in=student_ids, date__in=dates)
    justif_map = {(j.student_id, j.date): j for j in justifications}
    
    daily_records = {}
    for session in queryset.select_related('student', 'group', 'student__class_assigned').order_by('-date', 'student__full_name'):
        key = (session.student_id, session.date)
        if key not in daily_records:
            daily_records[key] = {
                'student': session.student,
                'group': session.group,
                'date': session.date,
                'sessions': {1: None, 2: None, 3: None, 4: None}
            }
        daily_records[key]['sessions'][session.session_number] = session.status
        
    result = []
    for key, record in daily_records.items():
        s_vals = [s for s in record['sessions'].values() if s is not None]
        
        if not s_vals:
            daily_status = None
        elif 'Absent' in s_vals:
            daily_status = 'Absent'
        elif 'Late' in s_vals:
            daily_status = 'Late'
        else:
            daily_status = 'Present'
            
        justif = justif_map.get(key)
        justif_status = None
        if daily_status == 'Absent':
            if justif:
                justif_status = justif.status
            else:
                justif_status = 'Non justifié'
                
        record['daily_status'] = daily_status
        record['justification'] = justif
        record['justification_status'] = justif_status
        result.append(record)
        
    return result
