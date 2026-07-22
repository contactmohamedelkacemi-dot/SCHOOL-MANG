from django.contrib import admin
from .models import Attendance

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'date', 'status')
    list_filter = ('date', 'status', 'module')
    search_fields = ('student__full_name', 'module__name')

admin.site.register(Attendance, AttendanceAdmin)
