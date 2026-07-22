from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student_list, name='list'),
    path('add/', views.student_create, name='create'),
    path('profile/<int:pk>/', views.student_profile, name='profile'),
    path('<int:pk>/edit/', views.student_update, name='update'),
    path('<int:pk>/delete/', views.student_delete, name='delete'),
    
    # Reports
    path('api/group/<int:group_id>/students/', views.get_students_by_group, name='get_students_by_group'),
    path('reports/teacher/', views.teacher_report_list, name='teacher_report_list'),
    path('reports/teacher/new/', views.teacher_report_create, name='teacher_report_create'),
    path('reports/admin/', views.admin_report_list, name='admin_report_list'),
    path('reports/admin/<int:pk>/review/', views.admin_report_review, name='admin_report_review'),
]
