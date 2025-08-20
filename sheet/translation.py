from modeltranslation.translator import register, TranslationOptions
from .models import StepTemplate

@register(StepTemplate)
class UserTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name', 'spec',)
    