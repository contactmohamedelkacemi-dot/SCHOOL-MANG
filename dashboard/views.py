from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from school_management.decorators import admin_required, teacher_required
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta
import json

from attendance.models import AttendanceSession, StudentRisk, Notification, Justification
from attendance.utils import calculate_student_risk
from students.models import Student, Report
from teachers.models import Teacher
from classes.models import Class, Module, Group

@login_required
def index(request):
    """
    Unified entry point that delegates to role-specific views.
    Used by LOGIN_REDIRECT_URL.
    """
    if request.user.role == 'admin':
        return redirect('dashboard:admin_dashboard')
    elif request.user.role == 'formateur':
        return redirect('dashboard:teacher_dashboard')
    elif request.user.role == 'stagiaire':
        return redirect('dashboard:student_dashboard')
    return redirect('accounts:login')

@admin_required
def admin_dashboard(request):
    total_students = Student.objects.count()
    total_teachers = Teacher.objects.count()
    total_classes = Class.objects.count()
    
    total_sessions = AttendanceSession.objects.count()
    
    present_count = AttendanceSession.objects.filter(status='Present').count()
    absent_count = AttendanceSession.objects.filter(status='Absent').count()
    late_count = AttendanceSession.objects.filter(status='Late').count()
    
    def pct(count, total):
        return round((count / total) * 100, 1) if total > 0 else 0
        
    present_pct = pct(present_count, total_sessions)
    absent_pct = pct(absent_count, total_sessions)
    late_pct = pct(late_count, total_sessions)
    
    pie_data = [present_count, absent_count, late_count]
    
    groups = Group.objects.annotate(
        total_sessions=Count('attendance_sessions'),
        present_sessions=Count('attendance_sessions', filter=Q(attendance_sessions__status='Present'))
    )
    bar_labels = []
    bar_data = []
    for g in groups:
        bar_labels.append(g.name)
        if g.total_sessions > 0:
            bar_data.append(round((g.present_sessions / g.total_sessions) * 100, 1))
        else:
            bar_data.append(0)
    
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    absences_over_time = (AttendanceSession.objects.filter(status='Absent', date__gte=thirty_days_ago)
                          .values('date')
                          .annotate(count=Count('id'))
                          .order_by('date'))
    
    line_labels = [str(a['date']) for a in absences_over_time]
    line_data = [a['count'] for a in absences_over_time]
    
    safe_count = StudentRisk.objects.filter(risk_level='Safe').count()
    at_risk_count = StudentRisk.objects.filter(risk_level='At Risk').count()
    critical_count = StudentRisk.objects.filter(risk_level='Critical').count()
    risk_pie_data = [safe_count, at_risk_count, critical_count]
    
    top_risk_profiles = StudentRisk.objects.select_related('student', 'student__class_assigned').order_by('-risk_score')[:5]
    
    top_absent_students = []
    for rp in top_risk_profiles:
        if rp.risk_score > 0:
            top_absent_students.append({
                'student': rp.student,
                'score': rp.risk_score,
                'alert': rp.risk_level
            })
            
    # Smart Alerts: Combine Pending Reports and Pending Justifications
    pending_reports_list = Report.objects.filter(status='Pending').select_related('student').order_by('-created_at')[:5]
    pending_justifications_list = Justification.objects.filter(status='Pending').select_related('student').order_by('-date')[:5]
    pending_reports = Report.objects.filter(status='Pending').count()
    
    smart_alerts = []
    for r in pending_reports_list:
        smart_alerts.append({
            'type': 'REPORT',
            'student': r.student.full_name,
            'title': r.title,
            'subtype': r.report_type,
            'priority': r.priority,
            'is_flagged': r.is_flagged,
            'timestamp': r.created_at,
            'id': r.id
        })
    for j in pending_justifications_list:
        # Fallback to date since created_at requires migration
        timestamp = j.date
        try:
            if hasattr(j, 'created_at') and j.created_at:
                timestamp = j.created_at
        except:
            pass
            
        smart_alerts.append({
            'type': 'JUSTIFICATION',
            'student': j.student.full_name,
            'title': 'Justification Submitted',
            'subtype': f"Date: {j.date}",
            'priority': 'Medium',
            'is_flagged': False,
            'timestamp': timestamp,
            'id': j.id
        })
    
    # Sort smart_alerts by timestamp descending
    smart_alerts.sort(key=lambda x: x['timestamp'] if x['timestamp'] else timezone.now(), reverse=True)

    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_classes': total_classes,
        'total_attendance': total_sessions,
        'present_pct': present_pct,
        'absent_pct': absent_pct,
        'late_pct': late_pct,
        'pie_data': json.dumps(pie_data),
        'risk_pie_data': json.dumps(risk_pie_data),
        'bar_labels': json.dumps(bar_labels),
        'bar_data': json.dumps(bar_data),
        'line_labels': json.dumps(line_labels),
        'line_data': json.dumps(line_data),
        'top_absent_students': top_absent_students,
        'pending_reports': pending_reports,
        'smart_alerts': smart_alerts[:10], # Limit to 10 most recent
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@teacher_required
def teacher_dashboard(request):
    try:
        teacher = Teacher.objects.get(user=request.user)
        
        # Strictly fetch ONLY groups assigned to this teacher
        groups = Group.objects.filter(teachers=teacher).select_related('class_assigned').distinct()
        total_groups = groups.count()
        
        # Unique students from these groups
        students = Student.objects.filter(groups__teachers=teacher).distinct()
        total_students = students.count()
        
        # Strictly fetch ONLY schedules assigned to this teacher
        from schedule.models import GroupSchedule
        schedules = GroupSchedule.objects.filter(teacher=teacher).select_related('group', 'module').order_by('day', 'session_number')
        total_sessions = schedules.count()
        
        total_modules = GroupSchedule.objects.filter(teacher=teacher).values_list('module', flat=True).distinct().count()
        
        # Organize schedule into a structured timetable for the template
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        sessions = [1, 2, 3, 4]
        session_times = {
            1: '08:00 - 10:00',
            2: '10:00 - 12:00',
            3: '14:00 - 16:00',
            4: '16:00 - 18:00',
        }
        
        schedule_grid = {day: {s: None for s in sessions} for day in days}
        for schedule in schedules:
            if schedule.day in schedule_grid and schedule.session_number in sessions:
                schedule_grid[schedule.day][schedule.session_number] = schedule
                
        # Flatten the grid for easy template iteration
        schedule_data = []
        for day in days:
            day_sessions = []
            for s in sessions:
                day_sessions.append({
                    'number': s,
                    'time': session_times[s],
                    'schedule': schedule_grid[day][s]
                })
            schedule_data.append({
                'day': day,
                'sessions': day_sessions
            })
            
        # Add schedule summary to each group
        for group in groups:
            group_schedules = [s for s in schedules if s.group_id == group.id]
            sched_by_day = {}
            for gs in group_schedules:
                sched_by_day.setdefault(gs.day, []).append(str(gs.session_number))
                
            summary_parts = []
            for day in days:
                if day in sched_by_day:
                    summary_parts.append(f"{day[:3]}({','.join(sched_by_day[day])})")
                    
            group.schedule_summary = "Sessions: " + ", ".join(summary_parts) if summary_parts else "No sessions scheduled"
            
        # Attendance Statistics
        attendance = AttendanceSession.objects.filter(group__teachers=teacher)
        total_att = attendance.count()
        
        present = attendance.filter(status='Present').count()
        absent = attendance.filter(status='Absent').count()
        late = attendance.filter(status='Late').count()
        
        if total_att > 0:
            present_pct = (present / total_att) * 100
            absent_pct = (absent / total_att) * 100
            late_pct = (late / total_att) * 100
        else:
            present_pct = absent_pct = late_pct = 0
            
        # Attendance per group
        bar_labels = []
        bar_data = []
        group_attendance_stats = groups.annotate(
            total_sessions=Count('attendance_sessions'),
            present_sessions=Count('attendance_sessions', filter=Q(attendance_sessions__status='Present'))
        )
        for g in group_attendance_stats:
            bar_labels.append(g.name)
            if g.total_sessions > 0:
                bar_data.append(round((g.present_sessions / g.total_sessions) * 100, 1))
            else:
                bar_data.append(0)
            
    except Teacher.DoesNotExist:
        groups = []
        schedule_data = []
        total_groups = total_students = total_modules = total_sessions = 0
        present = absent = late = total_att = 0
        present_pct = absent_pct = late_pct = 0
        bar_labels = []
        bar_data = []
        
    context = {
        'groups': groups,
        'schedule_data': schedule_data,
        'total_groups': total_groups,
        'total_students': total_students,
        'total_modules': total_modules,
        'total_sessions': total_sessions,
        'present_pct': round(present_pct, 1),
        'absent_pct': round(absent_pct, 1),
        'late_pct': round(late_pct, 1),
        'pie_data': json.dumps([present, absent, late]),
        'bar_labels': json.dumps(bar_labels),
        'bar_data': json.dumps(bar_data),
        'has_data': total_groups > 0,
        'has_attendance_data': total_att > 0
    }
    return render(request, 'dashboard/teacher_dashboard.html', context)

@login_required
def student_dashboard(request):
    if request.user.role != 'stagiaire':
        return redirect('accounts:login')
        
    try:
        student = request.user.student
    except Exception:
        return render(request, 'dashboard/student_dashboard.html', {'error': 'Profile not found.'})
        
    # Absences & Justifications Logic
    attendance_records = AttendanceSession.objects.filter(student=student)
    
    # Calculate Attendance Rate
    total_sessions = attendance_records.count()
    present_count = attendance_records.filter(status='Present').count()
    late_count = attendance_records.filter(status='Late').count()
    absent_count = attendance_records.filter(status='Absent').count()
    
    attendance_rate = round((present_count / total_sessions) * 100) if total_sessions > 0 else 100
    
    pie_data = [present_count, absent_count, late_count]
    
    # Group Absences by Date
    absent_sessions = attendance_records.filter(status='Absent').order_by('-date')
    
    # Pre-fetch justifications
    justifications = Justification.objects.filter(student=student)
    justif_map = {j.date: j for j in justifications}
    
    absences_by_date = {}
    for session in absent_sessions:
        if session.date not in absences_by_date:
            absences_by_date[session.date] = {
                'date': session.date,
                'sessions': [],
                'justification': justif_map.get(session.date),
                'status': 'Non justifié' # Default
            }
        absences_by_date[session.date]['sessions'].append(session.session_number)
        
    total_absences = len(absences_by_date)
    justified_absences = 0
    pending_justifications = 0
    
    for dt, data in absences_by_date.items():
        data['sessions'].sort()
        if data['justification']:
            data['status'] = data['justification'].status # Pending, Approved, Rejected
            if data['status'] == 'Approved':
                justified_absences += 1
            elif data['status'] == 'Pending':
                pending_justifications += 1
                
    absence_list = list(absences_by_date.values())
    
    # --- REAL-TIME INTELLIGENCE ---
    today = timezone.now().date()
    current_time = timezone.now().time()
    current_day_name = today.strftime('%A')
    
    # 1. Today Status
    today_sessions_records = attendance_records.filter(date=today)
    today_status = "Not marked"
    if today_sessions_records.exists():
        if today_sessions_records.filter(status='Absent').exists():
            today_status = "Absent"
        elif today_sessions_records.filter(status='Late').exists():
            today_status = "Late"
        else:
            today_status = "Present"
            
    # 2. Next Session Prediction
    from schedule.models import GroupSchedule
    group = student.groups.first()
    schedules = []
    next_session = None
    
    if group:
        schedules = GroupSchedule.objects.filter(group=group).select_related('module', 'teacher').order_by('day', 'session_number')
        
        # Build logic to find "next" based on current day and time
        # Helper: dynamically extract start hour from the GroupSchedule model
        def get_start_hour(sched):
            if sched.time:
                return sched.time.hour
            display_str = sched.get_session_number_display()
            if display_str and ':' in display_str:
                try:
                    return int(display_str.split(':')[0])
                except Exception:
                    pass
            return 24 # Fallback
            
        today_schedules = [s for s in schedules if s.day == current_day_name]
        today_schedules.sort(key=lambda s: s.session_number)
        
        for s in today_schedules:
            start_hour = get_start_hour(s)
            if start_hour > current_time.hour or (start_hour <= current_time.hour < start_hour + 2):
                # If it's currently running or in the future today
                next_session = s
                break
                
        # If no session left today, find the first session of tomorrow (or next available day)
        if not next_session:
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            try:
                today_idx = days_order.index(current_day_name)
            except ValueError:
                today_idx = 0
                
            for offset in range(1, 8):
                check_day = days_order[(today_idx + offset) % 7]
                day_schedules = [s for s in schedules if s.day == check_day]
                if day_schedules:
                    day_schedules.sort(key=lambda s: s.session_number)
                    next_session = day_schedules[0]
                    break

    # 3. Absence Severity (Risk Level)
    from attendance.models import StudentRisk
    student_risk = StudentRisk.objects.filter(student=student).first()
    risk_level = student_risk.risk_level if student_risk else 'Safe'

    # --- END REAL-TIME INTELLIGENCE ---
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    sessions = [1, 2, 3, 4]
    
    schedule_grid = {day: {s: None for s in sessions} for day in days}
    for schedule in schedules:
        if schedule.day in schedule_grid and schedule.session_number in sessions:
            schedule_grid[schedule.day][schedule.session_number] = schedule
            
    schedule_data = []
    for day in days:
        day_sessions = []
        for s in sessions:
            day_sessions.append({
                'number': s,
                'schedule': schedule_grid[day][s]
            })
        schedule_data.append({
            'day': day,
            'sessions': day_sessions
        })
        
    context = {
        'student': student,
        'total_absences': total_absences,
        'justified_absences': justified_absences,
        'pending_justifications': pending_justifications,
        'attendance_rate': attendance_rate,
        'absence_list': absence_list,
        'schedule_data': schedule_data,
        'pie_data': json.dumps(pie_data),
        'today_status': today_status,
        'next_session': next_session,
        'risk_level': risk_level,
    }
    return render(request, 'dashboard/student_dashboard.html', context)

from .forms import AdminUserCreationForm
from django.contrib.auth import get_user_model
from django.contrib import messages
import random
import string
from datetime import date

@admin_required
def admin_create_user(request):
    User = get_user_model()
    created_user_data = None
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Auto-generate username if blank
            if not username:
                base_username = full_name.lower().replace(' ', '_')
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                    
            # Auto-generate password if blank
            if not password:
                chars = string.ascii_letters + string.digits + '!@#$%^&*'
                password = ''.join(random.choice(chars) for _ in range(12))
                
            # Create the User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                is_profile_complete=False,  # Force profile completion on login
                must_change_password=True   # Force password change on first login
            )
            
            # Create corresponding Profile
            if role == 'formateur':
                phone = form.cleaned_data.get('phone')
                Teacher.objects.create(
                    user=user,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    cin=f"PENDING-{user.id}", # Placeholder
                    address="Please update your address",
                    date_of_birth=date(2000, 1, 1), # Placeholder
                    gender="Male", # Placeholder
                    specialty="To Be Determined" # Placeholder
                )
            elif role == 'stagiaire':
                class_assigned = form.cleaned_data.get('class_assigned')
                group_assigned = form.cleaned_data.get('group_assigned')
                
                student = Student.objects.create(
                    user=user,
                    full_name=full_name,
                    code=username, # Use username as code placeholder
                    date_of_birth=date(2005, 1, 1), # Placeholder
                    class_assigned=class_assigned,
                    address="Please update your address",
                    parent_name="Please update",
                    parent_phone="Please update"
                )
                
                if group_assigned:
                    group_assigned.students.add(student)
                    
            created_user_data = {
                'username': username,
                'password': password,
                'role': dict(AdminUserCreationForm.ROLE_CHOICES).get(role),
                'full_name': full_name
            }
            messages.success(request, f"User {full_name} created successfully!")
    else:
        form = AdminUserCreationForm()
        
    return render(request, 'dashboard/create_user.html', {
        'form': form,
        'created_user': created_user_data
    })

from django.http import JsonResponse

@admin_required
def admin_reset_password(request, user_id):
    if request.method == 'POST':
        User = get_user_model()
        user_to_reset = get_object_or_404(User, pk=user_id)
        
        # Generate new random password
        chars = string.ascii_letters + string.digits + '!@#$%^&*'
        new_password = ''.join(random.choice(chars) for _ in range(12))
        
        # Securely hash and save the new password
        user_to_reset.set_password(new_password)
        user_to_reset.must_change_password = True
        user_to_reset.save()
        
        # Pass the plain text password once via messages (stored in secure session)
        messages.success(request, f"PASSWORD_RESET:{new_password}")
        
        # Redirect back to where they came from
        next_url = request.POST.get('next', 'dashboard:admin_dashboard')
        return redirect(next_url)
    return redirect('dashboard:admin_dashboard')

from .forms import TeacherProfileCompletionForm, StudentProfileCompletionForm

@login_required
def complete_profile(request):
    if request.user.is_profile_complete:
        return redirect('dashboard:index')
        
    if request.user.role == 'formateur':
        profile = request.user.teacher
        form_class = TeacherProfileCompletionForm
    elif request.user.role == 'stagiaire':
        profile = request.user.student
        form_class = StudentProfileCompletionForm
    else:
        # Admin or other role does not need completion
        request.user.is_profile_complete = True
        request.user.save()
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.is_profile_complete = True
            request.user.save()
            messages.success(request, "Profile completed successfully! Welcome aboard.")
            return redirect('dashboard:index')
    else:
        # Clear the placeholder values so the user is forced to enter real ones
        initial_data = {}
        if request.user.role == 'formateur':
            if profile.cin.startswith('PENDING-'): initial_data['cin'] = ''
            if profile.address.startswith('Please update'): initial_data['address'] = ''
        elif request.user.role == 'stagiaire':
            if profile.address.startswith('Please update'): initial_data['address'] = ''
            if profile.parent_name.startswith('Please update'): initial_data['parent_name'] = ''
            if profile.parent_phone.startswith('Please update'): initial_data['parent_phone'] = ''
            
        form = form_class(instance=profile, initial=initial_data)
        
    return render(request, 'dashboard/complete_profile.html', {
        'form': form,
        'role': request.user.role
    })

from teachers.forms import TeacherProfileUpdateForm

@teacher_required
def teacher_profile(request):
    teacher = request.user.teacher
    
    # Statistics
    total_groups = Group.objects.filter(teachers=teacher).count()
    total_students = Student.objects.filter(groups__teachers=teacher).distinct().count()
    
    from schedule.models import GroupSchedule
    total_sessions = GroupSchedule.objects.filter(teacher=teacher).count()
    
    # Attendance Performance
    teacher_sessions = AttendanceSession.objects.filter(group__teachers=teacher)
    total_att = teacher_sessions.count()
    present_att = teacher_sessions.filter(status__in=['Present', 'Late']).count()
    attendance_rate = round((present_att / total_att) * 100, 1) if total_att > 0 else 0
    
    context = {
        'teacher': teacher,
        'total_groups': total_groups,
        'total_students': total_students,
        'total_sessions': total_sessions,
        'attendance_rate': attendance_rate
    }
    return render(request, 'teachers/profile.html', context)

@teacher_required
def teacher_profile_edit(request):
    teacher = request.user.teacher
    if request.method == 'POST':
        form = TeacherProfileUpdateForm(request.POST, request.FILES, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard:teacher_profile')
    else:
        form = TeacherProfileUpdateForm(instance=teacher)
        
    return render(request, 'teachers/profile_edit.html', {'form': form})

@login_required
def student_profile(request):
    if request.user.role != 'stagiaire':
        return redirect('accounts:login')
        
    student = request.user.student
    
    # Analytics & Risk Level
    risk_score, risk_level, trend_direction, stats = calculate_student_risk(student)
    
    # Justification statistics
    justifications = Justification.objects.filter(student=student)
    justified_absences = justifications.filter(status='Approved').count()
    pending_justifications = justifications.filter(status='Pending').count()
    
    reports = student.reports.select_related('teacher', 'group').order_by('-created_at')
    
    context = {
        'student': student,
        'reports': reports,
        'attendance_rate': stats['attendance_rate'],
        'total_absences': stats['absent'],
        'justified_absences': justified_absences,
        'pending_justifications': pending_justifications,
        'risk_level': risk_level
    }
    return render(request, 'students/profile.html', context)
    
