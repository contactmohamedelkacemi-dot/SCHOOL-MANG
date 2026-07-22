from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    path('groups/', views.group_select, name='group_select'),
    path('groups/<int:group_id>/', views.group_schedule_view, name='group_schedule_view'),
    path('groups/<int:group_id>/add/', views.group_schedule_add, name='group_schedule_add'),
    path('groups/<int:group_id>/assign/', views.group_schedule_assign, name='group_schedule_assign'),
    path('<int:pk>/delete/', views.group_schedule_delete, name='group_schedule_delete'),
]
