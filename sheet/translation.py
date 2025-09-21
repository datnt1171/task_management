from modeltranslation.translator import register, TranslationOptions
from .models import StepTemplate, FormularTemplate, ProductTemplate

@register(StepTemplate)
class StepTemplateTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name', 'spec',)

@register(FormularTemplate)
class FormularTemplateTranslationOptions(TranslationOptions):
    fields = ('spray_type',)

@register(ProductTemplate)
class ProductTemplateTranslationOptions(TranslationOptions):
    fields = ('type',)
    