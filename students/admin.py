from django.contrib import admin
from .models import Student

class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'code', 'class_assigned', 'parent_phone')
    list_filter = ('class_assigned',)
    search_fields = ('full_name', 'code', 'parent_name')

admin.site.register(Student, StudentAdmin)
