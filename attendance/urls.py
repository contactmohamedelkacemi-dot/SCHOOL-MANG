from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Admin URLs
    path('groups/', views.group_select, name='group_select'),
    path('groups/<int:group_id>/', views.group_attendance, name='group_attendance'),
    path('justifications/', views.justification_list, name='justification_list'),
    path('justifications/create/', views.justification_create, name='justification_create'),
    path('justifications/<int:pk>/approve/', views.justification_approve, name='justification_approve'),
    path('justifications/<int:pk>/reject/', views.justification_reject, name='justification_reject'),
    path('reports/', views.attendance_report, name='attendance_report'),
    path('reports/export/csv/', views.attendance_export_csv, name='attendance_export_csv'),
    path('reports/export/pdf/', views.attendance_export_pdf_view, name='attendance_export_pdf'),
    
    # Teacher URLs
    path('teacher/groups/', views.teacher_group_select, name='teacher_group_select'),
    path('teacher/groups/<int:group_id>/', views.teacher_group_attendance, name='teacher_group_attendance'),
    
    # Student URLs
    path('student/justification/submit/', views.student_submit_justification, name='student_submit_justification'),
]
