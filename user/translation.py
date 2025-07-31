from modeltranslation.translator import register, TranslationOptions
from .models import User, Department, Role, BusinessFunction

@register(User)
class UserTranslationOptions(TranslationOptions):
    fields = ('first_name', 'last_name',)
    

@register(Department)
class DepartmenTranslationOptions(TranslationOptions):
    fields = ('name',)
    

@register(Role)
class RoleTranslationOptions(TranslationOptions):
    fields = ('name',)
    

@register(BusinessFunction)
class BusinessFunctionTranslationOptions(TranslationOptions):
    fields = ('name',)