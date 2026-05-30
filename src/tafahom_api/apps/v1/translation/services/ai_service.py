import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def call_ai_translation(text: str) -> dict | None:
    """
    Call the AI translation service with a strict timeout.
    Returns: {"source": "ai", "animations": [...]} on success, or None on failure/timeout.
    """
    timeout_seconds = getattr(settings, 'AI_TIMEOUT_SECONDS', 3)
    # Get the AI service endpoint from settings, fallback to a local mock if not set
    ai_url = getattr(settings, 'AI_TEXT_TO_GLOSS_BASE_URL', 'http://localhost:8000/api/ai/translate/')
    
    logger.info("AI request start for text: %s (Timeout: %ss)", text, timeout_seconds)
    
    try:
        # Example payload and headers
        payload = {"text": text}
        response = requests.post(ai_url, json=payload, timeout=timeout_seconds)
        
        response.raise_for_status()
        
        data = response.json()
        
        # Expected response from AI might be {"gloss": ["hello", "world"]} 
        # or we normalize it to "animations"
        # Since requirements say AI returns {"source": "ai", "animations": [...]}:
        animations = data.get("animations") or data.get("gloss") or data.get("translation", [])
        if not isinstance(animations, list):
            animations = [animations]
            
        logger.info("AI request successful. Duration: %s seconds", response.elapsed.total_seconds())
        
        return {
            "source": "ai",
            "animations": animations
        }
        
    except requests.exceptions.Timeout:
        logger.warning("AI timeout for text: %s (Exceeded %s seconds)", text, timeout_seconds)
        return None
    except requests.exceptions.RequestException as e:
        logger.error("AI failure for text: %s. Error: %s", text, e)
        return None
    except Exception as e:
        logger.error("Unexpected AI failure for text: %s. Error: %s", text, e)
        return None
