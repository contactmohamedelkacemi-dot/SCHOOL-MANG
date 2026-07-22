from django.urls import path
from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.index, name='index'), # Route dispatcher
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/create-user/', views.admin_create_user, name='admin_create_user'),
    path('admin/reset-password/<int:user_id>/', views.admin_reset_password, name='admin_reset_password'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('teacher/profile/', views.teacher_profile, name='teacher_profile'),
    path('teacher/profile/edit/', views.teacher_profile_edit, name='teacher_profile_edit'),
    path('student/profile/', views.student_profile, name='student_profile'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
]
