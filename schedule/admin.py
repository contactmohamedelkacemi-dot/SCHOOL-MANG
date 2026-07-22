from django.contrib import admin
from .models import Schedule

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_assigned', 'module', 'day', 'time')
    list_filter = ('class_assigned', 'day')
    search_fields = ('module__name',)

admin.site.register(Schedule, ScheduleAdmin)
