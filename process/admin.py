from django.contrib import admin
from .models import Process, ProcessUser, Action, ProcessActionRole, ProcessField

admin.site.register(Process)
admin.site.register(ProcessUser)
admin.site.register(Action)
admin.site.register(ProcessActionRole)
admin.site.register(ProcessField)
