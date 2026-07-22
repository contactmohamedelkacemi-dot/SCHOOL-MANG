from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    path('', views.class_list, name='list'),
    path('add/', views.class_create, name='create'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/add/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_update, name='group_update'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),
]
