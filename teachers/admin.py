from django.contrib import admin
from .models import Teacher

class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'cin', 'specialty')
    list_filter = ('gender', 'specialty')
    search_fields = ('full_name', 'email', 'cin')

admin.site.register(Teacher, TeacherAdmin)
