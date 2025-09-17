from django.utils.translation import get_language

def get_localized_column(base_column, available_locales=None):
    
    if available_locales is None:
        available_locales = {'en', 'vi', 'zh_hant'}
    
    lang = get_language()  # e.g. 'vi', 'en'
    
    # Handle special case for traditional Chinese
    if lang == 'zh-hant':
        lang = 'zh_hant'
    
    # Build localized column name
    localized_column = f"{base_column}_{lang}"
    
    # Check if this locale is available
    expected_localized_columns = {f"{base_column}_{locale}" for locale in available_locales}
    
    if localized_column in expected_localized_columns:
        return localized_column
    else:
        # Fallback to base column without locale suffix
        return base_column