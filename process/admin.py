from django.contrib import admin
from .models import Process, ProcessUser, ActionType, Action, ProcessUserAction, ProcessField

admin.site.register(Process)
admin.site.register(ProcessUser)
admin.site.register(ActionType)
admin.site.register(Action)
admin.site.register(ProcessUserAction)
admin.site.register(ProcessField)
