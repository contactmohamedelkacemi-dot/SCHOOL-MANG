from django.contrib import admin
from .models import Grade

class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'score')
    list_filter = ('module',)
    search_fields = ('student__full_name', 'module__name')

admin.site.register(Grade, GradeAdmin)
