from django.contrib import admin
from .models import Class, Module

class ClassAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'class_assigned', 'coefficient')
    list_filter = ('teacher', 'class_assigned')
    search_fields = ('name',)

admin.site.register(Class, ClassAdmin)
admin.site.register(Module, ModuleAdmin)
