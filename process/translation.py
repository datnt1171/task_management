from modeltranslation.translator import register, TranslationOptions
from .models import Process, Action, ProcessField

@register(Process)
class ProcessTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)
    
    
@register(Action)
class ActionTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)
    
    
@register(ProcessField)
class ProcessFieldTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)