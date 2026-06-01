from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import YouTubeTranslation
from .serializers import YouTubeTranslationSerializer, YouTubeTranslationCreateSerializer
from .services.translation import start_youtube_translation
from tafahom_api.apps.v1.notifications.models import Notification
from tafahom_api.common.decorators import require_token_and_plan

from tafahom_api.apps.v1.translation.services.youtube_service import (
    get_youtube_video_info,
    YouTubeAuthError,
    YouTubeNotFoundError,
    YouTubeInvalidURLError,
    YouTubeProcessingError
)
from tafahom_api.apps.v1.youtube.services.extraction import extract_transcript
from tafahom_api.apps.v1.translation.services.pipeline_service import normalize_arabic
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
from tafahom_api.apps.v1.translation.services.streaming_translation_service import TranslationPipelineService

from asgiref.sync import async_to_sync

import logging
logger = logging.getLogger(__name__)

from tafahom_api.apps.v1.youtube.services.extraction import get_youtube_video_duration_fast

MAX_VIDEO_DURATION_MINUTES = 30

class YouTubeTranslateView(APIView):
    permission_classes = [IsAuthenticated]

    # Use require_token_and_plan just to verify plan level, we'll manually check tokens so we don't deduct yet.
    @require_token_and_plan(token_cost=0, min_plan="basic", feature_name="YouTube Translation")
    def post(self, request):
        serializer = YouTubeTranslationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        youtube_url = serializer.validated_data['youtube_url']
        subscription = request.subscription
        
        # 1. Manually check if user has enough tokens (without consuming)
        if not subscription.can_consume(15):
            return Response(
                {"detail": _("Not enough tokens. YouTube Translation requires 15 tokens.")},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        # 2. Check video length
        try:
            duration_seconds = get_youtube_video_duration_fast(youtube_url)
            
            if duration_seconds is None:
                video_info = get_youtube_video_info(youtube_url)
                duration_seconds = video_info.get("duration", 0)
                
            if duration_seconds > (MAX_VIDEO_DURATION_MINUTES * 60):
                return Response(
                    {"detail": _(f"Video is too long. Maximum allowed duration is {MAX_VIDEO_DURATION_MINUTES} minutes.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except YouTubeInvalidURLError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (YouTubeAuthError, YouTubeNotFoundError, YouTubeProcessingError) as e:
            with transaction.atomic():
                YouTubeTranslation.objects.create(
                    user=request.user,
                    youtube_url=youtube_url,
                    status="failed",
                    tokens_used=0,
                    source="upload_fallback"
                )
            logger.info("Returning upload fallback response")
            return Response(
                {
                    "success": False,
                    "requires_upload": True,
                    "error": "Unable to process this YouTube video. Please upload the video file directly."
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": _("An unexpected error occurred during validation.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            # Create translation record (No token deduction here!)
            translation = YouTubeTranslation.objects.create(
                user=request.user,
                youtube_url=youtube_url,
                status="processing",
                tokens_used=15
            )
            
            # Send Notification
            Notification.objects.create(
                user=request.user,
                type="youtube",
                title="YouTube Translation Started",
                message="Your YouTube translation has started."
            )

        # Dispatch background task
        start_youtube_translation(translation.id)

        return Response({
            "success": True,
            "translation_id": translation.id,
            "status": "processing",
            "tokens_used": 15,
            "remaining_tokens": subscription.remaining_tokens(),
        }, status=status.HTTP_202_ACCEPTED)

class YouTubeTranslationHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = YouTubeTranslationSerializer

    def get_queryset(self):
        return YouTubeTranslation.objects.filter(user=self.request.user)

class YouTubeTranslationDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = YouTubeTranslationSerializer
    
    def get_queryset(self):
        return YouTubeTranslation.objects.filter(user=self.request.user)


class YouTubeSignTranslateView(APIView):
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=0, min_plan="basic", feature_name="YouTube Sign Translate")
    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response({
                "success": False,
                "requires_upload": True,
                "error": "No YouTube URL provided."
            })

        subscription = request.subscription
        if not subscription.can_consume(10):
            return Response({
                "success": False,
                "requires_upload": True,
                "error": "Not enough tokens. Please top up your account."
            })

        # Step 1: Extract transcript
        transcript = None
        source = None
        try:
            transcript, source = extract_transcript(url)
        except Exception as e:
            logger.warning(f"Transcript extraction failed: {e}")

        if not transcript:
            return Response({
                "success": False,
                "requires_upload": True,
                "error": "Unable to process this YouTube video. Please upload the video directly."
            })

        # Step 2: NLP → Gloss
        gloss_tokens = []
        try:
            ai_result = async_to_sync(
                TranslationPipelineService._text_to_gloss_client.text_to_gloss
            )(transcript)
            raw = (
                ai_result.get("gloss_translation")
                or ai_result.get("gloss")
                or ai_result.get("text")
                or transcript
            )
            normalized = normalize_arabic(str(raw))
            gloss_tokens = [t for t in normalized.split() if t]
        except Exception as e:
            logger.warning(f"NLP failed for sign translate: {e}, using raw transcript")
            gloss_tokens = [t for t in normalize_arabic(transcript).split() if t]

        # Step 3: Gloss → Animations
        animations_result = translate_to_animation_names(" ".join(gloss_tokens))
        animations = animations_result.get("animations", [])

        if not animations:
            animations_result = translate_to_animation_names(transcript)
            animations = animations_result.get("animations", [])

        # Step 4: Consume tokens
        with transaction.atomic():
            subscription.consume(10)

        return Response({
            "success": True,
            "source": source or "transcript",
            "transcript": transcript,
            "gloss": gloss_tokens,
            "animations": animations,
        })
