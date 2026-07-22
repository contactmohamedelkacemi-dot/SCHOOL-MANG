from django.shortcuts import render, redirect, get_object_or_404
from .models import Class, Group
from .forms import ClassForm, GroupForm
from school_management.decorators import admin_required
from django.contrib import messages

@admin_required
def class_list(request):
    classes = Class.objects.all()
    return render(request, 'classes/class_list.html', {'classes': classes})

@admin_required
def class_create(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class created successfully.')
            return redirect('classes:list')
    else:
        form = ClassForm()
    return render(request, 'classes/class_form.html', {'form': form, 'is_update': False})

@admin_required
def group_list(request):
    groups = Group.objects.select_related('class_assigned').prefetch_related('teachers', 'students').all()
    return render(request, 'classes/group_list.html', {'groups': groups})

@admin_required
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group created successfully.')
            return redirect('classes:group_list')
    else:
        form = GroupForm()
    return render(request, 'classes/group_form.html', {'form': form, 'is_update': False})

@admin_required
def group_update(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group updated successfully.')
            return redirect('classes:group_list')
    else:
        form = GroupForm(instance=group)
    return render(request, 'classes/group_form.html', {'form': form, 'is_update': True})

@admin_required
def group_delete(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Group deleted successfully.')
        return redirect('classes:group_list')
    return render(request, 'classes/group_confirm_delete.html', {'group': group})
