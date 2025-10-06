from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from .models import Process, ProcessUser, Action, ProcessActionRole, ProcessField, FieldCondition
from workflow_engine.models import Transition, ActionTransition


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


class ActionTransitionInline(admin.TabularInline):
    model = ActionTransition
    extra = 0
    fields = ('action',)
    show_change_link = True
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "action":
            # Get the transition from the URL to find its process
            if hasattr(self, 'parent_obj') and self.parent_obj:
                kwargs["queryset"] = Action.objects.filter(process=self.parent_obj.process)
            else:
                # Try to get from URL path
                import re
                match = re.search(r'/transition/([^/]+)/change/', request.path)
                if match:
                    try:
                        transition = Transition.objects.get(id=match.group(1))
                        kwargs["queryset"] = Action.objects.filter(process=transition.process)
                    except Transition.DoesNotExist:
                        kwargs["queryset"] = Action.objects.none()
                else:
                    kwargs["queryset"] = Action.objects.none()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_formset(self, request, obj=None, **kwargs):
        # Store the parent object for use in formfield_for_foreignkey
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)


class TransitionProcessInline(admin.TabularInline):
    model = Transition
    extra = 0
    fields = ('current_state', 'next_state',)
    show_change_link = True


class TransitionAdmin(admin.ModelAdmin):
    list_display = ('process', 'current_state', 'next_state', 'created_at')
    list_filter = ('process',)
    inlines = [ActionTransitionInline]


class ProcessAdmin(TranslationAdmin):
    list_display = ('name', 'version', 'prefix', 'is_active', 'created_at')
    list_filter = ('name', 'is_active')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [
        ProcessFieldInline, 
        ProcessActionInline, 
        ProcessActionRoleInline, 
        TransitionProcessInline,
    ]


class ActionAdmin(TranslationAdmin):
    list_display = ('name', 'action_type', 'process')
    list_filter = ('action_type', 'process')


class FieldConditionInline(admin.TabularInline):
    model = FieldCondition
    extra = 0
    fk_name = 'field'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "condition_field":
            # Get the parent ProcessField from the URL
            if hasattr(self, 'parent_obj') and self.parent_obj:
                # Filter by the parent field's process AND smaller order
                kwargs["queryset"] = ProcessField.objects.filter(
                    process=self.parent_obj.process,
                    order__lt=self.parent_obj.order
                )
            else:
                # Try to get from URL path
                import re
                match = re.search(r'/processfield/([^/]+)/change/', request.path)
                if match:
                    try:
                        parent_field = ProcessField.objects.get(id=match.group(1))
                        kwargs["queryset"] = ProcessField.objects.filter(
                            process=parent_field.process,
                            order__lt=parent_field.order
                        )
                    except ProcessField.DoesNotExist:
                        kwargs["queryset"] = ProcessField.objects.none()
                else:
                    kwargs["queryset"] = ProcessField.objects.none()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_formset(self, request, obj=None, **kwargs):
        # Store the parent object for use in formfield_for_foreignkey
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)


class FieldConditionAdmin(admin.ModelAdmin):
    list_display = ('field', 'condition_field', 'operator', 'value')
    list_filter = ('operator', 'field__process')


class ProcessFieldAdmin(TranslationAdmin):
    list_display = ('name', 'process', 'field_type', 'order', 'required')
    list_filter = ('process',)
    ordering = ('process', 'order',)
    inlines = [FieldConditionInline]


class ProcessUserAdmin(admin.ModelAdmin):
    list_display = ('process', 'user')
    list_filter = ('process',)
    search_fields = ('user',)


class ProcessActionRoleAdmin(admin.ModelAdmin):
    list_display = ('process', 'action', 'role_type')
    list_filter = ('process',)
    ordering = ('process',)


class ActionTransitionAdmin(admin.ModelAdmin):
    list_display = ('transition', 'action', 'created_at')
    list_filter = ('transition__process',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "action":
            # Get transition from add/change URL
            import re
            match = re.search(r'transition=([^&]+)', request.GET.get('transition', ''))
            if match:
                try:
                    transition = Transition.objects.get(id=match.group(1))
                    kwargs["queryset"] = Action.objects.filter(process=transition.process)
                except Transition.DoesNotExist:
                    pass
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Process, ProcessAdmin)
admin.site.register(ProcessUser, ProcessUserAdmin)
admin.site.register(Action, ActionAdmin)
admin.site.register(ProcessActionRole, ProcessActionRoleAdmin)
admin.site.register(ProcessField, ProcessFieldAdmin)
admin.site.register(FieldCondition, FieldConditionAdmin)
admin.site.register(Transition, TransitionAdmin)
admin.site.register(ActionTransition, ActionTransitionAdmin)