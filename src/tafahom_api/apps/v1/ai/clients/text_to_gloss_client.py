import json
from django.conf import settings
from .base import BaseAIClient
from tafahom_api.apps.v1.translation.sign_map import ANIMATION_MAP, SIGN_MAP, SYNONYM_MAP


# Build once at import time — these don't change at runtime
_ANIMATION_MAP_KEYS = " ".join(ANIMATION_MAP.keys())
_SIGN_MAP_KEYS      = " ".join(SIGN_MAP.keys())
_SYNONYM_MAP_STR    = json.dumps(SYNONYM_MAP, ensure_ascii=False)

_SYSTEM_PROMPT = """\
You are an Arabic Sign Language gloss translator for a Unity avatar system.

Your task:
Convert Arabic user text into ONLY valid sign words that exist in the sign dictionary.

STRICT RULES:
* ONLY use words from the provided sign dictionary.
* NEVER invent words.
* NEVER paraphrase.
* NEVER generate similar sounding words.
* NEVER autocorrect.
* NEVER use synonyms unless they exist in SYNONYM_MAP.
* If a word exists in SYNONYM_MAP, replace it with its mapped value.
* If SYNONYM_MAP value is null, REMOVE the word completely.
* If a word is unknown, keep it EXACTLY as written.
* Output ONLY Arabic gloss words separated by spaces.
* No explanations. No punctuation. No extra text.

The backend will later match these words with Unity animations.

Available sign dictionary:
{animation_keys}
{sign_keys}

Synonym normalization dictionary:
{synonym_map}

Examples:
Input: حرائق كبيره
Output: حريق مشكله

Input: الإسعاف وصل
Output: اسعاف

Input: انا مبسوط
Output: مبسوط

Input: مقهور جرح
Output: مقهور جرح

Input: في نار
Output: حريق

IMPORTANT:
* Deterministic output only.
* Preserve exact dataset vocabulary.
* Never generate unseen words.
* Never change unknown emotional words.
* If unsure, preserve the original word exactly.
""".format(
    animation_keys=_ANIMATION_MAP_KEYS,
    sign_keys=_SIGN_MAP_KEYS,
    synonym_map=_SYNONYM_MAP_STR,
)


class TextToGlossClient(BaseAIClient):
    base_url = settings.AI_TEXT_TO_GLOSS_BASE_URL

    async def text_to_gloss(self, text: str):
        if not text or not text.strip():
            raise ValueError("Text is empty")

        prompt = _SYSTEM_PROMPT + f"\nUser Input:\n{text.strip()}\n"

        payload = {"prompt": prompt}

        try:
            return await self._post_json("/generate", json=payload)
        except Exception:
            return {"gloss": ""}
