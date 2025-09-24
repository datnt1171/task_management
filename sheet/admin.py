from django.contrib import admin
from .models import StepTemplate, FormularTemplate, ProductTemplate, FinishingSheet

class ProductTemplateInline(admin.TabularInline):
    model = ProductTemplate
    extra = 0
    ordering = ['name']
    fields = ('code', 'name', 'ratio', 
              'type', 'type_en', 'type_vi', 'type_zh_hant', 
              'unit',)
    show_change_link = True

class FormularTemplateAdmin(admin.ModelAdmin):
    list_display = ('code', 'viscosity', 'created_at', 'updated_at')
    list_filter = ('viscosity',)
    search_fields = ('code',)
    ordering = ('code',)
    inlines = [ProductTemplateInline]

admin.site.register(FormularTemplate, FormularTemplateAdmin)
admin.site.register(StepTemplate)
admin.site.register(FinishingSheet)
