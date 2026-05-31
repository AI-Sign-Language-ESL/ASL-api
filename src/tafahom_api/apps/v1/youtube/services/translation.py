import logging
import threading
import asyncio
from django.db import transaction
from tafahom_api.apps.v1.youtube.models import YouTubeTranslation
from tafahom_api.apps.v1.notifications.models import Notification
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
from tafahom_api.apps.v1.translation.services.streaming_translation_service import TranslationPipelineService
from tafahom_api.apps.v1.youtube.services.extraction import extract_transcript
from django.conf import settings
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

def process_youtube_translation_task(translation_id):
    """
    Background task to process youtube translation
    """
    translation = YouTubeTranslation.objects.filter(id=translation_id).first()
    if not translation:
        return
        
    user = translation.user

    try:
        # Step 1: Extract Transcript
        logger.info(f"Extracting transcript for {translation.youtube_url}")
        transcript = extract_transcript(translation.youtube_url)
        
        if not transcript:
            raise ValueError("No speech detected in the video")

        # Step 2: Translation to Animations
        logger.info(f"Translating transcript...")
        # Use Unity SignMatcher/Translation logic similar to UnityTranslateView
        animations_data = None
        
        try:
            # Try NLP first
            ai_result = async_to_sync(TranslationPipelineService._text_to_gloss_client.text_to_gloss)(transcript)
            raw = ai_result.get("gloss_translation") or ai_result.get("gloss") or ai_result.get("text") or transcript
            animations_data = translate_to_animation_names(str(raw))
        except Exception as e:
            logger.warning(f"NLP failed for youtube translation: {e}, falling back to SignMatcher")
            try:
                from tafahom_api.apps.v1.translation.services.unity_sign_matcher_client import UnitySignMatcherClient
                client = UnitySignMatcherClient()
                animations = async_to_sync(client.match)(transcript)
                if animations:
                    animations_data = {"animations": animations, "unknown_words": []}
            except Exception as e2:
                logger.warning(f"UnitySignMatcher failed: {e2}")

        if not animations_data:
            # Final fallback
            animations_data = translate_to_animation_names(transcript)

        # Step 3: Update DB and Consume Tokens
        with transaction.atomic():
            translation.transcript = transcript
            translation.animation_data = animations_data.get("animations", [])
            translation.status = "completed"
            translation.save()
            
            # Consume tokens
            subscription = getattr(user, "subscription", None)
            if subscription:
                subscription.consume(15)
            
            # Send Notification
            Notification.objects.create(
                user=user,
                type="youtube",
                title="YouTube Translation Ready",
                message="Your YouTube translation is ready.",
                action_url=f"/youtube?id={translation.id}"
            )
            
    except Exception as e:
        logger.error(f"YouTube translation failed: {e}")
        with transaction.atomic():
            translation.status = "failed"
            translation.save()
            
            Notification.objects.create(
                user=user,
                type="youtube",
                title="YouTube Translation Failed",
                message="We could not process your YouTube video."
            )

def start_youtube_translation(translation_id):
    """
    Dispatches the background thread
    """
    thread = threading.Thread(target=process_youtube_translation_task, args=(translation_id,))
    thread.daemon = True
    thread.start()
