import re
import logging

logger = logging.getLogger(__name__)

# Predefined Synonym Mapping
SYNONYM_MAP = {
    "نسيبي": "nseby",
    "نسيبه": "nseby",
    "قريبي": "nseby",
    "كيف حالك": "kef_halak",
}

# Example phrase mapping could also be implemented dynamically 
# but per instructions we prioritize phrase matching.

def normalize_arabic_text(text: str) -> str:
    """
    Normalizes Arabic text by removing punctuation, extra spaces,
    and handling common diacritics if necessary.
    """
    if not text:
        return ""
        
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def match_sign(text: str) -> dict:
    """
    Deterministic fallback sign matcher.
    Returns: {"source": "sign_matcher", "animations": [...]}
    """
    if not text:
        return {"source": "sign_matcher", "animations": []}

    from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
    
    # We defer to the unified animation matching engine
    match_result = translate_to_animation_names(text)
    animations = match_result["animations"]

    logger.info("Sign Matcher fallback used for: %s. Result: %s", text, animations)
    return {
        "source": "sign_matcher",
        "animations": animations
    }
