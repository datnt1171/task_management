from django.contrib import admin
from .models import Task, TaskData, TaskActionLog, TaskPermission
# Register your models here.
admin.site.register(Task)
admin.site.register(TaskData)
admin.site.register(TaskActionLog)
admin.site.register(TaskPermission)