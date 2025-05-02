from django.contrib import admin
from .models import State, StateType, Transition, ActionTransition
# Register your models here.
admin.site.register(State)
admin.site.register(StateType)
admin.site.register(Transition)
admin.site.register(ActionTransition)