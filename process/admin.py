from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from .models import Process, ProcessUser, Action, ProcessActionRole, ProcessField
from workflow_engine.models import Transition


class ProcessFieldInline(TranslationTabularInline):
    model = ProcessField
    extra = 0
    ordering = ['order']
    fields = ('name', 'description', 'field_type', 'order', 'required', 'options',)
    show_change_link = True


class ProcessActionInline(TranslationTabularInline):
    model = Action
    extra = 0
    fields = (
        'name', 'description', 'action_type', 'process',
    )


class ProcessActionRoleInline(admin.TabularInline):
    model = ProcessActionRole
    extra = 0
    fields = (
        'action', 'role_type',
        'specific_user', 'specific_role', 'specific_department',
    )
    show_change_link = True
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "action":
            # Get the process ID from the URL
            if request.resolver_match and request.resolver_match.kwargs.get('object_id'):
                process_id = request.resolver_match.kwargs['object_id']
                kwargs["queryset"] = Action.objects.filter(process_id=process_id)
            else:
                # For new Process objects, show no actions until saved
                kwargs["queryset"] = Action.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TransitionProcessInline(admin.TabularInline):
    model = Transition
    extra = 0
    fields = ('current_state', 'next_state',)
    show_change_link = True

class ProcessAdmin(TranslationAdmin):
    list_display = ('name', 'version', 'prefix', 'is_active', 'created_at')
    list_filter = ('name', 'is_active')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [ProcessFieldInline, ProcessActionInline, ProcessActionRoleInline, TransitionProcessInline]


class ActionAdmin(TranslationAdmin):
    list_display = ('name', 'action_type', 'process')
    list_filter = ('action_type', 'process')


class ProcessFieldAdmin(TranslationAdmin):
    list_display = ('name', 'process', 'field_type', 'order', 'required')
    list_filter = ('field_type', 'required')


admin.site.register(Process, ProcessAdmin)
admin.site.register(ProcessUser)
admin.site.register(Action, ActionAdmin)
admin.site.register(ProcessActionRole)
admin.site.register(ProcessField, ProcessFieldAdmin)