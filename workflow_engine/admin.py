from django.contrib import admin
from django.db import models
from .models import State, Transition, ActionTransition
from process.models import Process, Action


class ProcessFilter(admin.SimpleListFilter):
    title = 'Process'
    parameter_name = 'process'
    
    def lookups(self, request, model_admin):
        processes = Process.objects.all()
        return [(p.id, f"{p.name} (v{p.version})") for p in processes]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                models.Q(action__process_id=self.value()) & 
                models.Q(transition__process_id=self.value())
            )
        return queryset


class ActionTransitionAdminAdvanced(admin.ModelAdmin):
    list_display = ('get_process', 'action', 'get_current_state', 'get_next_state',)
    list_filter = (ProcessFilter,)
    search_fields = ('action__name', 'transition__current_state__name', 'transition__next_state__name')
    ordering = ('transition__process', 'action')
    
    def get_process(self, obj):
        return f"{obj.transition.process.name} (v{obj.transition.process.version})"
    get_process.short_description = 'Process'
    
    def get_current_state(self, obj):
        return obj.transition.current_state
    get_current_state.short_description = 'From State'
    
    def get_next_state(self, obj):
        return obj.transition.next_state
    get_next_state.short_description = 'To State'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Get selected process from custom filter
        process_id = request.GET.get('process')
        
        if db_field.name == "action" and process_id:
            kwargs["queryset"] = Action.objects.filter(process_id=process_id)
        elif db_field.name == "transition" and process_id:
            kwargs["queryset"] = Transition.objects.filter(process_id=process_id)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'action__process', 
            'transition__process', 
            'transition__current_state', 
            'transition__next_state'
        )


admin.site.register(State)
admin.site.register(Transition)
admin.site.register(ActionTransition, ActionTransitionAdminAdvanced)