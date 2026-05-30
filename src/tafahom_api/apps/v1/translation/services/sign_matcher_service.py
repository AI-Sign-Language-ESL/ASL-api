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
    normalized_text = normalize_arabic_text(text)
    animations = []
    
    if not normalized_text:
        return {"source": "sign_matcher", "animations": animations}

    # 1. Phrase Matching
    # Sort synonym map keys by length descending to match longest phrases first
    sorted_phrases = sorted(SYNONYM_MAP.keys(), key=lambda k: len(k.split()), reverse=True)
    
    remaining_text = normalized_text
    
    for phrase in sorted_phrases:
        if phrase in remaining_text:
            logger.info("Sign Matcher phrase match found: %s", phrase)
            animations.append(SYNONYM_MAP[phrase])
            # Remove matched phrase to process rest (simplistic approach)
            remaining_text = remaining_text.replace(phrase, " ")
            
    # Clean up remaining text after phrase extraction
    remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
    
    # 2. Word Matching
    if remaining_text:
        words = remaining_text.split()
        for word in words:
            # Check synonyms
            if word in SYNONYM_MAP:
                animations.append(SYNONYM_MAP[word])
            else:
                # If no synonym, we could map it directly to English ascii mapping if needed,
                # but for now we just append the word as is if it's meant to be an animation name
                # or skip. We'll append an ascii/latin mapping representation or the word itself.
                # Per the example, we map words directly to "kef", "halak", "ya", "mohamed"
                # Let's map directly
                animations.append(word)

    logger.info("Sign Matcher fallback used for: %s. Result: %s", text, animations)
    return {
        "source": "sign_matcher",
        "animations": animations
    }
