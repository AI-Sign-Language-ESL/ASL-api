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
            
        synonym_phrase = apply_synonyms(norm_phrase)
        if not synonym_phrase:
            continue
            
        words = synonym_phrase.split()
        node = root
        for word in words:
            node = node.setdefault(word, {})
        
        # Prevent duplicate normalized keys from overwriting the first intended animation
        if "_anim" not in node:
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

    words = text_clean.split()
    n = len(words)
    
    # 2️⃣ Recursive Longest-Match-First Strategy
    # This guarantees that the globally longest phrases in the sentence are prioritized.
    # It checks lengths from (end - start) down to 1.
    def match_segment(start, end):
        if start >= end:
            return [], [], [], []
            
        best_match = None
        best_i = -1
        best_k = -1
        best_phrase = None
        
        # Iterate over possible phrase lengths, from longest down to 1
        for k in range(end - start, 0, -1):
            for i in range(start, end - k + 1):
                node = _TRIE
                found = True
                for j in range(i, i + k):
                    word = words[j]
                    if word in node:
                        node = node[word]
                    else:
                        found = False
                        break
                
                if found and "_anim" in node:
                    best_match = node["_anim"]
                    best_i = i
                    best_k = k
                    best_phrase = " ".join(words[i:i + k])
                    break # Found the first (leftmost) match of length k
            
            if best_match:
                break # Found the globally longest match in this segment
                
        if best_match:
            # Recursively process the segment before the match
            left_anims, left_unknowns, left_mphrases, left_mwords = match_segment(start, best_i)
            # Recursively process the segment after the match
            right_anims, right_unknowns, right_mphrases, right_mwords = match_segment(best_i + best_k, end)
            
            anims = left_anims + [best_match] + right_anims
            unknowns = left_unknowns + right_unknowns
            
            mphrases = list(left_mphrases)
            mwords = list(left_mwords)
            if best_k > 1:
                mphrases.append(best_phrase)
                logger.info("MATCHED PHRASE   : %r -> %r", best_phrase, best_match)
            else:
                mwords.append(best_phrase)
                logger.info("MATCHED WORD     : %r -> %r", best_phrase, best_match)
                
            mphrases.extend(right_mphrases)
            mwords.extend(right_mwords)
            
            return anims, unknowns, mphrases, mwords
        else:
            # No match found in this segment at all. All words are unknown.
            unmatched = words[start:end]
            for u in unmatched:
                logger.warning("UNKNOWN WORD     : %r", u)
            return [], unmatched, [], []

    animations, unknown_words, matched_phrases, matched_words = match_segment(0, n)

    if not unknown_words and len(animations) == 1 and matched_phrases and matched_phrases[0] == text_clean:
        logger.info("MATCH TYPE       : FULL SENTENCE")
        logger.info("MATCHED PHRASE   : %r -> %r", text_clean, animations[0])

    logger.info("MATCHED PHRASES  : %s", matched_phrases)
    logger.info("MATCHED WORDS    : %s", matched_words)
    logger.info("UNKNOWN WORDS    : %s", unknown_words)
    logger.info("FINAL ANIMATIONS : %s", animations)
    logger.info("=" * 50)

    return {
        "animations": animations,
        "unknown_words": unknown_words,
    }