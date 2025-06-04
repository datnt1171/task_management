from modeltranslation.translator import register, TranslationOptions
from .models import State

@register(State)
class StateTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)