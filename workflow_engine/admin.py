from django.contrib import admin
from .models import State, Transition, ActionTransition
# Register your models here.
admin.site.register(State)
admin.site.register(Transition)
admin.site.register(ActionTransition)