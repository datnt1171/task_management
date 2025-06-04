# core/utils.py
from django.utils.translation import get_language

def get_current_language():
    """Get currently active language"""
    return get_language()

def get_translated_field(obj, field_name, language=None):
    """Get translated field value with fallback"""
    if language is None:
        language = get_current_language()
    
    # Try to get language-specific field
    translated_field = f"{field_name}_{language}"
    if hasattr(obj, translated_field):
        value = getattr(obj, translated_field)
        if value:
            return value
    
    # Fallback to English
    english_field = f"{field_name}_en"
    if hasattr(obj, english_field):
        return getattr(obj, english_field)
    
    # Fallback to default field
    return getattr(obj, field_name, '')
