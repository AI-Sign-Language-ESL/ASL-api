import logging
from collections import defaultdict

from ..sign_map import (
    ANIMATION_MAP
)
from .normalization import normalize_arabic, apply_synonyms

logger = logging.getLogger(__name__)


def _build_trie(phrase_map):
    """Build a word-level Trie from phrase → animation map.
    Returns (root, max_depth) where root is the trie and max_depth is the deepest phrase in words.
    """
    root = {}
    max_depth = 0
    
    # Normalize keys in the map before building the trie so lookups don't fail
    for phrase, anim in phrase_map.items():
        norm_phrase = normalize_arabic(phrase)
        if not norm_phrase:
            continue
            
        words = norm_phrase.split()
        node = root
        for word in words:
            node = node.setdefault(word, {})
        node["_anim"] = anim
        if len(words) > max_depth:
            max_depth = len(words)
    return root, max_depth


# Build trie once at module load
_TRIE, _MAX_PHRASE_DEPTH = _build_trie(ANIMATION_MAP)


def translate_to_animation_names(text):
    animations = []
    unknown_words = []
    matched_phrases = []
    matched_words = []

    logger.info("=" * 50)
    logger.info("SIGN TRANSLATION INPUT (Raw): %r", text)

    # 1️⃣ Normalize text and apply synonyms
    norm_text = normalize_arabic(text)
    text_clean = apply_synonyms(norm_text)
    
    logger.info("SIGN TRANSLATION INPUT (Normalized): %r", text_clean)

    if not text_clean:
         return {"animations": animations, "unknown_words": unknown_words}

    # 2️⃣ Check FULL sentence match first
    # Note: ANIMATION_MAP values must be looked up carefully since text_clean is normalized
    # We can check if it exists in the Trie directly as a single path instead of looking at raw dict
    words = text_clean.split()
    n = len(words)
    
    # Let's check full sentence match against trie
    node = _TRIE
    full_match = None
    for word in words:
        if word in node:
            node = node[word]
        else:
            node = None
            break
            
    if node and "_anim" in node:
        full_match = node["_anim"]
        animations.append(full_match)
        matched_phrases.append(text_clean)

        logger.info("MATCH TYPE       : FULL SENTENCE")
        logger.info("MATCHED PHRASE   : %r -> %r", text_clean, full_match)
        logger.info("FINAL ANIMATIONS : %s", animations)
        logger.info("=" * 50)

        return {
            "animations": animations,
            "unknown_words": unknown_words,
        }

    # 3️⃣ Trie-based greedy phrase/word matching (O(n * max_depth))
    # This guarantees longest phrase match first because we search outward to limit, 
    # and keep updating last_match as long as we stay on a valid path.
    i = 0

    while i < n:
        node = _TRIE
        last_match = None
        matched_k = 0

        # Traverse the trie word by word up to max phrase depth
        limit = min(i + _MAX_PHRASE_DEPTH, n)
        for j in range(i, limit):
            word = words[j]
            if word in node:
                node = node[word]
                if "_anim" in node:
                    last_match = node["_anim"]
                    matched_k = j - i + 1
            else:
                break

        if last_match:
            phrase = " ".join(words[i:i + matched_k])
            animations.append(last_match)
            if matched_k > 1:
                matched_phrases.append(phrase)
                logger.info("MATCHED PHRASE   : %r -> %r", phrase, last_match)
            else:
                matched_words.append(phrase)
                logger.info("MATCHED WORD     : %r -> %r", phrase, last_match)
            i += matched_k
        else:
            unmatched_word = words[i]
            unknown_words.append(unmatched_word)
            logger.warning("UNKNOWN WORD     : %r", unmatched_word)
            i += 1

    logger.info("MATCHED PHRASES  : %s", matched_phrases)
    logger.info("MATCHED WORDS    : %s", matched_words)
    logger.info("UNKNOWN WORDS    : %s", unknown_words)
    logger.info("FINAL ANIMATIONS : %s", animations)
    logger.info("=" * 50)

    return {
        "animations": animations,
        "unknown_words": unknown_words,
    }