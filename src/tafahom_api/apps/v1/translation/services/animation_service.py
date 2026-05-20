import logging

from ..sign_map import (
    ANIMATION_MAP
)

logger = logging.getLogger(__name__)


def translate_to_animation_names(text):
    animations = []
    unknown_words = []
    matched_phrases = []
    matched_words = []

    text_clean = text.strip()

    logger.info("=" * 50)
    logger.info("SIGN TRANSLATION INPUT: %r", text_clean)

    # 1️⃣ Check FULL sentence match first
    if text_clean in ANIMATION_MAP:
        anim = ANIMATION_MAP[text_clean]
        animations.append(anim)
        matched_phrases.append(text_clean)

        logger.info("MATCH TYPE       : FULL SENTENCE")
        logger.info("MATCHED PHRASE   : %r -> %r", text_clean, anim)
        logger.info("FINAL ANIMATIONS : %s", animations)
        logger.info("=" * 50)

        return {
            "animations": animations,
            "unknown_words": unknown_words,
        }

    # 2️⃣ Greedy phrase/word matching
    words = text_clean.split()
    i = 0
    n = len(words)

    while i < n:
        match_found = False
        # Try matching consecutive sub-phrases of length k starting from maximum down to 1
        for k in range(n - i, 0, -1):
            phrase = " ".join(words[i:i+k])
            if phrase in ANIMATION_MAP:
                anim = ANIMATION_MAP[phrase]
                animations.append(anim)
                if k > 1:
                    matched_phrases.append(phrase)
                    logger.info("MATCHED PHRASE   : %r -> %r", phrase, anim)
                else:
                    matched_words.append(phrase)
                    logger.info("MATCHED WORD     : %r -> %r", phrase, anim)
                i += k
                match_found = True
                break

        if not match_found:
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