from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from .models import Process, ProcessUser, Action, ProcessActionRole, ProcessField


class ProcessFieldInline(TranslationTabularInline):
    model = ProcessField
    extra = 0
    ordering = ['order']
    fields = ('name', 'field_type', 'order', 'required', 'options',)
    show_change_link = True


class ProcessActionRoleInline(admin.TabularInline):
    model = ProcessActionRole
    extra = 0
    fields = (
        'action', 'role_type',
        'specific_user', 'specific_role', 'specific_department',
    )
    show_change_link = True


class ProcessAdmin(TranslationAdmin):
    list_display = ('name', 'version', 'prefix', 'is_active', 'created_at')
    list_filter = ('name', 'is_active')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [ProcessFieldInline, ProcessActionRoleInline,]


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