from modeltranslation.translator import register, TranslationOptions
from .models import StepTemplate

@register(StepTemplate)
class StepTemplateTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name', 'spec',)
    