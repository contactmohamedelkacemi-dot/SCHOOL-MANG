from django.shortcuts import render, redirect, get_object_or_404
from .models import Student
from accounts.models import User
from .forms import StudentForm
from school_management.decorators import admin_required
from django.contrib import messages

@admin_required
def student_list(request):
    students = Student.objects.select_related('class_assigned').all()
    return render(request, 'students/student_list.html', {'students': students})

@admin_required
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            code = form.cleaned_data['code']
            if User.objects.filter(username=code).exists():
                messages.error(request, f"User with code {code} already exists.")
            else:
                user = User.objects.create_user(username=code, password=code, role='stagiaire')
                student = form.save(commit=False)
                student.user = user
                student.save()
                messages.success(request, 'Student created successfully.')
                return redirect('students:list')
    else:
        form = StudentForm()
    return render(request, 'students/student_form.html', {'form': form, 'is_update': False})

from django.db.models import Count, Q

from attendance.models import Justification
from attendance.utils import calculate_student_risk

@admin_required
def student_profile(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    # Intelligent Analytics
    risk_score, risk_level, trend_direction, stats = calculate_student_risk(student)
    
    # Reports
    reports = student.reports.select_related('teacher', 'group').order_by('-created_at')
    
    # Justification statistics
    justifications = Justification.objects.filter(student=student)
    justified_absences = justifications.filter(status='Approved').count()
    pending_justifications = justifications.filter(status='Pending').count()
    
    context = {
        'student': student,
        'reports': reports,
        'attendance_rate': stats['attendance_rate'],
        'total_absences': stats['absent'],
        'justified_absences': justified_absences,
        'pending_justifications': pending_justifications,
        'risk_level': risk_level,
        'total_sessions': stats['total'],
        'present_sessions': stats['present'],
        'absent_sessions': stats['absent'],
        'late_sessions': stats['late'],
        'absence_rate': round(stats['absence_rate'], 1),
        'risk_score': risk_score,
        'trend_direction': trend_direction,
        'recent_absence_rate': round(stats['recent_absence_rate'], 1),
    }
    return render(request, 'students/profile.html', context)

@admin_required
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully.')
            return redirect('students:list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/student_form.html', {'form': form, 'is_update': True})

@admin_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        user = student.user
        student.delete()
        if user:
            user.delete()
        messages.success(request, 'Student deleted successfully.')
        return redirect('students:list')
    return render(request, 'students/student_confirm_delete.html', {'student': student})

# --- REPORTS SYSTEM ---

from django.http import JsonResponse
from school_management.decorators import teacher_required
from .models import Report
from .forms import ReportForm

@teacher_required
def get_students_by_group(request, group_id):
    """AJAX endpoint to get students for a specific group."""
    try:
        teacher = request.user.teacher
        from classes.models import Group
        group = get_object_or_404(Group, pk=group_id, teachers=teacher)
        students = group.students.all().order_by('full_name')
        student_list = [{'id': s.id, 'name': s.full_name} for s in students]
        return JsonResponse({'students': student_list})
    except Exception:
        return JsonResponse({'error': 'Not authorized'}, status=403)

@teacher_required
def teacher_report_list(request):
    teacher = request.user.teacher
    reports = Report.objects.filter(teacher=teacher).select_related('student', 'group').order_by('-created_at')
    return render(request, 'reports/teacher_report_list.html', {'reports': reports})

@teacher_required
def teacher_report_create(request):
    teacher = request.user.teacher
    if request.method == 'POST':
        form = ReportForm(teacher, request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.teacher = teacher
            # Strict validation: student must belong to the selected group
            if report.student not in report.group.students.all():
                messages.error(request, 'Selected student does not belong to the selected group.')
            else:
                report.save()
                messages.success(request, 'Report submitted successfully.')
                return redirect('students:teacher_report_list')
    else:
        form = ReportForm(teacher)
    return render(request, 'reports/teacher_report_form.html', {'form': form})

@admin_required
def admin_report_list(request):
    reports = Report.objects.select_related('student', 'teacher', 'group').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter in dict(Report.STATUS_CHOICES):
        reports = reports.filter(status=status_filter)
        
    return render(request, 'reports/admin_report_list.html', {'reports': reports, 'current_filter': status_filter})

@admin_required
def admin_report_review(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'review':
            report.status = 'Reviewed'
            report.admin_comment = request.POST.get('admin_comment', '')
            report.save()
            messages.success(request, 'Report marked as reviewed.')
        elif action == 'delete':
            report.delete()
            messages.success(request, 'Report deleted successfully.')
            
    return redirect('students:admin_report_list')
