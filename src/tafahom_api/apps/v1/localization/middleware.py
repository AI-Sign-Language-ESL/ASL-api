from django.utils import translation
from django.conf import settings


class LanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language_code = request.COOKIES.get("django_language", settings.LANGUAGE_CODE)

        # FIX: Ensure the language is actually supported before activating
        supported_codes = [code for code, name in settings.LANGUAGES]
        if language_code not in supported_codes:
            language_code = settings.LANGUAGE_CODE

        translation.activate(language_code)
        request.LANGUAGE_CODE = language_code

        response = self.get_response(request)

        translation.deactivate()

        return response
