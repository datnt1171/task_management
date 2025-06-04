from modeltranslation.translator import register, TranslationOptions
from .models import User, Department, Role

@register(User)
class UserTranslationOptions(TranslationOptions):
    fields = ('first_name', 'last_name',)
    

@register(Department)
class DepartmenTranslationOptions(TranslationOptions):
    fields = ('name',)
    

@register(Role)
class RoleTranslationOptions(TranslationOptions):
    fields = ('name',)