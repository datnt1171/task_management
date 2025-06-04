# core/middleware.py
import logging
from django.utils.translation import activate
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)

class APILanguageMiddleware(MiddlewareMixin):
    """
    Global middleware for language handling across all apps
    """
    
    def process_request(self, request):
        # Get language from various sources
        language = self._get_language_from_request(request)
        
        # Validate language (ensure it's supported)
        django_language = self._validate_language(language)
        
        # Activate language globally
        activate(django_language)
        
        # Store in request for views
        request.current_language = django_language
        
        # Log language switching (optional)
        if getattr(settings, 'DEBUG', False):
            logger.debug(f"Language activated: {django_language}")
    
    def process_response(self, request, response):
        # Add language info to response headers
        if hasattr(request, 'current_language'):
            response['X-Current-Language'] = request.current_language
        return response
    
    def _get_language_from_request(self, request):
        """Get language from request in priority order"""
        # 1. Custom header (highest priority)
        language = request.META.get('HTTP_X_LANGUAGE')
        if language:
            return language
        
        # 2. Query parameter (for debugging)
        language = request.GET.get('lang')
        if language:
            return language
        
        # 3. Accept-Language header
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if accept_language:
            return accept_language.split(',')[0].strip()[:2]
        
        # 4. Default
        return 'en'
    
    def _validate_language(self, language):
        """Validate language code against Django's LANGUAGES setting"""
        # Get supported languages from settings
        supported_languages = [lang[0] for lang in getattr(settings, 'LANGUAGES', [('en', 'English')])]
        
        # Return language if supported, otherwise default to English
        return language if language in supported_languages else 'en'