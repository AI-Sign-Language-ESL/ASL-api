from typing import List, Dict
from django.core.cache import cache
from django.conf import settings

from tafahom_api.apps.v1.localization.models import TranslationKey


class TranslationKeyService:
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    @staticmethod
    def _cache_key(key: str, language: str) -> str:
        return f"localization:translation:{key}:{language}"

    @staticmethod
    def get_translation(
        key: str,
        language: str = "en",
        fallback: str = "en",
    ) -> str:

        key = key.lower()
        cache_key = TranslationKeyService._cache_key(key, language)

        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        try:
            obj = TranslationKey.objects.get(key=key)

            text = obj.text_ar if language == "ar" else obj.text_en

            if not text and fallback != language:
                text = obj.text_ar if fallback == "ar" else obj.text_en

            if not text:
                text = key

            cache.set(cache_key, text, TranslationKeyService.CACHE_TIMEOUT)
            return text

        except TranslationKey.DoesNotExist:
            return key

    @staticmethod
    def get_bulk_translations(
        keys: List[str],
        language: str = "en",
        fallback: str = "en",
    ) -> Dict[str, str]:

        keys = [key.lower() for key in keys]

        translations: Dict[str, str] = {}
        missing_keys: List[str] = []

        for key in keys:
            cache_key = TranslationKeyService._cache_key(key, language)
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                translations[key] = cached_value
            else:
                missing_keys.append(key)

        if missing_keys:
            queryset = TranslationKey.objects.filter(key__in=missing_keys)
            found_keys = set()

            for obj in queryset:
                text = obj.text_ar if language == "ar" else obj.text_en

                if not text and fallback != language:
                    text = obj.text_ar if fallback == "ar" else obj.text_en

                if not text:
                    text = obj.key

                translations[obj.key] = text
                found_keys.add(obj.key)

                cache.set(
                    TranslationKeyService._cache_key(obj.key, language),
                    text,
                    TranslationKeyService.CACHE_TIMEOUT,
                )

            for key in missing_keys:
                if key not in found_keys:
                    translations[key] = key

        return translations

    @staticmethod
    def clear_translation_cache(key: str):
        key = key.lower()
        # Fallback if settings.LANGUAGES is not defined, prevents crash
        languages = getattr(
            settings, "LANGUAGES", [("en", "English"), ("ar", "Arabic")]
        )

        for lang_code, _ in languages:
            cache.delete(TranslationKeyService._cache_key(key, lang_code))

    @staticmethod
    def clear_all_translation_cache():
        """
        Safely clears translation cache.
        Tries to use wildcard deletion if supported (Redis),
        otherwise iterates through database keys to avoid wiping the entire cache.
        """
        # 1. Fast path: Wildcard deletion (Works with django-redis)
        if hasattr(cache, "delete_pattern"):
            # Matches pattern: localization:translation:*
            # This is O(1) or optimized scan depending on backend
            try:
                cache.delete_pattern("localization:translation:*")
                return
            except NotImplementedError:
                pass  # Fallback to manual deletion

        # 2. Universal fallback: Database iteration
        # Safe for Memcached or LocMemCache where wildcards aren't supported.
        # We only fetch the key strings to keep memory usage low.
        keys = TranslationKey.objects.values_list("key", flat=True)

        for key in keys:
            TranslationKeyService.clear_translation_cache(key)
