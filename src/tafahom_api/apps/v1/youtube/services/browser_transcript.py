import logging
from django.db import transaction
from asgiref.sync import async_to_sync

from tafahom_api.apps.v1.youtube.models import YouTubeTranslation
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
from tafahom_api.apps.v1.translation.services.sign_translation_service import normalize_arabic
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient

logger = logging.getLogger(__name__)


def process_browser_transcript(transcript, user, video_id="", title="", language="ar"):
    """
    Process a browser-submitted transcript through the NLP → Gloss → Sign pipeline.
    Returns the full result synchronously.
    """
    normalized = normalize_arabic(transcript)

    gloss_tokens = []
    try:
        ai_result = async_to_sync(
            TextToGlossClient().text_to_gloss
        )(normalized)
        raw = (
            ai_result.get("gloss_translation")
            or ai_result.get("gloss")
            or ai_result.get("text")
            or normalized
        )
        gloss_tokens = [t for t in normalize_arabic(str(raw)).split() if t]
    except Exception as e:
        logger.warning(f"NLP failed for browser transcript: {e}")
        gloss_tokens = [t for t in normalized.split() if t]

    animations_result = translate_to_animation_names(" ".join(gloss_tokens))
    animations = animations_result.get("animations", [])

    if not animations:
        animations_result = translate_to_animation_names(normalized)
        animations = animations_result.get("animations", [])

    with transaction.atomic():
        subscription = getattr(user, "subscription", None)
        tokens_used = 10

        if subscription:
            subscription.consume(tokens_used)

        translation = YouTubeTranslation.objects.create(
            user=user,
            youtube_url=f"https://youtube.com/watch?v={video_id}" if video_id else "",
            transcript=transcript,
            source="transcript",
            status="completed",
            tokens_used=tokens_used,
            animation_data=animations,
        )

    remaining = subscription.remaining_tokens() if subscription else 0

    return {
        "success": True,
        "translation_id": translation.id,
        "transcript": transcript,
        "gloss": gloss_tokens,
        "animations": animations,
        "tokens_used": tokens_used,
        "remaining_tokens": remaining,
    }
