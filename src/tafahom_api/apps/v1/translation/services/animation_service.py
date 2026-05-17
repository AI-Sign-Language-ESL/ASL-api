from ..sign_map import (
    ANIMATION_MAP
)


def translate_to_animation_names(text):

    words = text.split()

    animations = []

    unknown_words = []

    i = 0

    while i < len(words):

        found = False

        # ===============================
        # 3 WORD PHRASE
        # ===============================

        if i + 2 < len(words):

            phrase = (
                words[i]
                + " "
                + words[i + 1]
                + " "
                + words[i + 2]
            )

            if phrase in ANIMATION_MAP:

                animations.append(
                    ANIMATION_MAP[phrase]
                )

                i += 3

                found = True

        # ===============================
        # 2 WORD PHRASE
        # ===============================

        if (
            not found
            and i + 1 < len(words)
        ):

            phrase = (
                words[i]
                + " "
                + words[i + 1]
            )

            if phrase in ANIMATION_MAP:

                animations.append(
                    ANIMATION_MAP[phrase]
                )

                i += 2

                found = True

        # ===============================
        # SINGLE WORD
        # ===============================

        if not found:

            word = words[i]

            if word in ANIMATION_MAP:

                animations.append(
                    ANIMATION_MAP[word]
                )

            else:

                unknown_words.append(
                    word
                )

            i += 1

    return {
        "animations": animations,
        "unknown_words": unknown_words,
    }