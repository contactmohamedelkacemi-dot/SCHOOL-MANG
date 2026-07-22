from django.shortcuts import render, redirect, get_object_or_404
from .models import GroupSchedule
from classes.models import Group
from .forms import GroupScheduleForm
from school_management.decorators import admin_required
from django.contrib import messages

@admin_required
def group_select(request):
    groups = Group.objects.select_related('class_assigned').all()
    return render(request, 'schedule/group_select.html', {'groups': groups})

from teachers.models import Teacher
from classes.models import Module

@admin_required
def group_schedule_view(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    schedules = GroupSchedule.objects.filter(group=group)
    
    # Organize schedule by day and session for a grid view
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
            
    # Flatten the grid for easy template iteration without custom tags
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
            
    teachers = Teacher.objects.all()
    modules = Module.objects.all()
            
    return render(request, 'schedule/group_schedule.html', {
        'group': group, 
        'schedule_data': schedule_data,
        'teachers': teachers,
        'modules': modules
    })

@admin_required
def group_schedule_assign(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        # Concurrency safety note: In a true production app under heavy load, 
        # we might wrap this in a database transaction with select_for_update.
        form = GroupScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Session assigned successfully.')
        else:
            # Extract and display the first error message
            error_msg = "Failed to assign session."
            for field, errors in form.errors.items():
                for error in errors:
                    error_msg = error
                    break
                break
            messages.error(request, error_msg)
            
    return redirect('schedule:group_schedule_view', group_id=group.id)

@admin_required
def group_schedule_add(request, group_id):
    # Keeping this for backward compatibility if needed, but the new UI uses assign
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        form = GroupScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule added successfully.')
            return redirect('schedule:group_schedule_view', group_id=group.id)
    else:
        form = GroupScheduleForm(initial={'group': group})
    
    return render(request, 'schedule/group_schedule_form.html', {'form': form, 'group': group})

@admin_required
def group_schedule_delete(request, pk):
    schedule = get_object_or_404(GroupSchedule, pk=pk)
    group_id = schedule.group.id
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'Schedule deleted successfully.')
        return redirect('schedule:group_schedule_view', group_id=group_id)
    return render(request, 'schedule/schedule_confirm_delete.html', {'schedule': schedule})
