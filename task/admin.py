from django.contrib import admin
from .models import Task, TaskData, TaskActionLog, TaskPermission

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'state', 'created_at', 'created_by',)
    list_filter = ('state',)
    search_fields = ('title', 'created_by__username')


class TaskDataAdmin(admin.ModelAdmin):
    list_display = ('task__title', 'field', 'value',)
    search_fields = ('task__title',)


class TaskPermissionAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'user', 'role_type',)
    search_fields = ('task',)

admin.site.register(Task, TaskAdmin)
admin.site.register(TaskData, TaskDataAdmin)
admin.site.register(TaskActionLog)
admin.site.register(TaskPermission, TaskPermissionAdmin)