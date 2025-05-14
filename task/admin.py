from django.contrib import admin
from .models import Task, TaskData, TaskActionLog
# Register your models here.
admin.site.register(Task)
admin.site.register(TaskData)
admin.site.register(TaskActionLog)