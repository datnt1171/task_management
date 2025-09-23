from modeltranslation.translator import register, TranslationOptions
from .models import StepTemplate, FormularTemplate, ProductTemplate

@register(StepTemplate)
class StepTemplateTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name', 'spec', 'sanding',)

@register(ProductTemplate)
class ProductTemplateTranslationOptions(TranslationOptions):
    fields = ('type',)
    