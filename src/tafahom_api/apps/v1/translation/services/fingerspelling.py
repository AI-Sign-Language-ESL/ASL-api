import logging
import re
from tafahom_api.apps.v1.translation.sign_map import ANIMATION_MAP
from tafahom_api.apps.v1.translation.services.normalization import normalize_arabic

logger = logging.getLogger(__name__)

# Dynamically generate LETTER_MAP for all single Arabic characters in ANIMATION_MAP
LETTER_MAP = {
    k: v for k, v in ANIMATION_MAP.items()
    if len(k) == 1 and '\u0600' <= k <= '\u06FF'
}

# Context triggers that indicate the next word is likely a name
NAME_TRIGGERS = {
    "اسمي",
    "انا اسمي",
    "اسمه",
    "اسمها",
    "اسمك",
    "اسمكم",
    "اسمها ايه",
    "اسمك ايه",
    "اسمه ايه",
    "يا",
    "ده",
    "دي",
}

def is_probable_name(token: str, previous_tokens: list[str]) -> bool:
    """
    Check if a token is likely a name based on the preceding context.
    """
    if not previous_tokens:
        return False
        
    # Check 1-word trigger (e.g., "يا", "اسمي")
    if previous_tokens[-1] in NAME_TRIGGERS:
        return True
        
    # Check 2-word trigger (e.g., "انا اسمي")
    if len(previous_tokens) >= 2:
        two_word_context = f"{previous_tokens[-2]} {previous_tokens[-1]}"
        if two_word_context in NAME_TRIGGERS:
            return True
            
    return False

def fingerspell(word: str) -> list[str]:
    """
    Convert a word into a sequence of letter animations.
    Normalizes the text and ignores punctuation and spaces.
    """
    norm_word = normalize_arabic(word)
    clean_word = re.sub(r'[^\w]', '', norm_word)
    
    animations = []
    for char in clean_word:
        if char in LETTER_MAP:
            animations.append(LETTER_MAP[char])
        else:
            logger.warning("Fingerspelling: Character %r not found in LETTER_MAP.", char)
            
    return animations
