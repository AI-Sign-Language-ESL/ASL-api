from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

CACHE_PREFIX = "translation_ai_"

def get_cached_translation(normalized_text: str) -> dict | None:
    """
    Retrieve translation from cache based on normalized text.
    """
    if not normalized_text:
        return None
        
    cache_key = f"{CACHE_PREFIX}{normalized_text}"
    try:
        result = cache.get(cache_key)
        if result:
            logger.info("Cache hit for text: %s", normalized_text)
            return result
        else:
            logger.info("Cache miss for text: %s", normalized_text)
            return None
    except Exception as e:
        logger.error("Error retrieving from cache: %s", e)
        return None

def set_cached_translation(normalized_text: str, result: dict) -> None:
    """
    Cache a successful AI translation.
    """
    if not normalized_text or not result:
        return
        
    cache_key = f"{CACHE_PREFIX}{normalized_text}"
    timeout = getattr(settings, 'CACHE_TIMEOUT', 86400)
    
    try:
        cache.set(cache_key, result, timeout=timeout)
        logger.info("Cached successful translation for text: %s", normalized_text)
    except Exception as e:
        logger.error("Error setting cache: %s", e)
