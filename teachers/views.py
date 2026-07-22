from django.shortcuts import render, redirect, get_object_or_404
from .models import Teacher
from accounts.models import User
from .forms import TeacherForm
from school_management.decorators import admin_required
from django.contrib import messages

@admin_required
def teacher_list(request):
    teachers = Teacher.objects.all()
    return render(request, 'teachers/teacher_list.html', {'teachers': teachers})

@admin_required
def teacher_create(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data['email']
            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                messages.error(request, f"User with username {username} already exists.")
            else:
                user = User.objects.create_user(username=username, password=username, email=email, role='formateur')
                teacher = form.save(commit=False)
                teacher.user = user
                teacher.save()
                messages.success(request, 'Teacher created successfully.')
                return redirect('teachers:list')
    else:
        form = TeacherForm()
    return render(request, 'teachers/teacher_form.html', {'form': form, 'is_update': False})

@admin_required
def teacher_profile(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    
    from classes.models import Group
    from students.models import Student
    from schedule.models import GroupSchedule
    from attendance.models import AttendanceSession
    
    total_groups = Group.objects.filter(teachers=teacher).count()
    total_students = Student.objects.filter(groups__teachers=teacher).distinct().count()
    total_sessions = GroupSchedule.objects.filter(teacher=teacher).count()
    
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

@admin_required
def teacher_update(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        form = TeacherForm(request.POST, request.FILES, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Teacher updated successfully.')
            return redirect('teachers:list')
    else:
        form = TeacherForm(instance=teacher)
    return render(request, 'teachers/teacher_form.html', {'form': form, 'is_update': True})

@admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        user = teacher.user
        teacher.delete()
        if user:
            user.delete()
        messages.success(request, 'Teacher deleted successfully.')
        return redirect('teachers:list')
    return render(request, 'teachers/teacher_confirm_delete.html', {'teacher': teacher})
