import asyncio
import logging
import os
import subprocess
import httpx

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TranslationRequest, SignLanguageConfig
from drf_spectacular.utils import extend_schema

from .serializers import (
    TranslationRequestCreateSerializer,
    TranslationRequestStatusSerializer,
    SignLanguageConfigSerializer,
    TranslationRequestListSerializer,
    UnitySignResponseSerializer,
)
from .services.youtube_service import download_youtube_audio

from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
from tafahom_api.apps.v1.billing.services import consume_translation_token, consume_generation_token
from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)
from tafahom_api.apps.v1.translation.services.streaming_translation_service import (
    TranslationPipelineService,
)
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
from tafahom_api.apps.v1.translation.serializers import TextToSignSerializer
from tafahom_api.apps.v1.translation.sign_map import ANIMATION_MAP

from tafahom_api.common.decorators import require_token_and_plan

from tafahom_api.apps.v1.translation.services.cache_service import get_cached_translation, set_cached_translation
from tafahom_api.apps.v1.translation.services.ai_service import call_ai_translation
from tafahom_api.apps.v1.translation.services.sign_matcher_service import match_sign, normalize_arabic_text

logger = logging.getLogger(__name__)


# =====================================================
# SPEECH → TEXT
# =====================================================
class SpeechToTextView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=5, min_plan="basic", feature_name="Speech Mode", cost_type="speech_to_text")
    def post(self, request):
        subscription = request.subscription
        audio_file = request.FILES.get("file")

        if not audio_file:
            return Response(
                {"error": "No audio file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔒 Hard guard against silence / accidental taps
        if audio_file.size < 25_000:  # ~0.8s @ 16kHz PCM16
            logger.warning(
                "STT rejected: audio too small (%s bytes)",
                audio_file.size,
            )
            return Response({"text": ""}, status=status.HTTP_200_OK)

        client = SpeechToTextClient()

        try:
            result = async_to_sync(client.speech_to_text)(audio_file)
        except Exception as exc:
            logger.exception("STT client failure")
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        text = (result.get("text") or "").strip() if isinstance(result, dict) else ""

        if text:
            # Only consume tokens if there's actually a result
            with transaction.atomic():
                subscription.consume(5)

        return Response({
            "text": text,
            "remaining_tokens": subscription.remaining_tokens(),
        }, status=status.HTTP_200_OK)


# =====================================================
# META VIEWS
# =====================================================
class SignLanguageListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignLanguageConfigSerializer
    queryset = SignLanguageConfig.objects.all().order_by("id")


class MyTranslationRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestListSerializer

    def get_queryset(self):
        return TranslationRequest.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class TranslationStatusView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestStatusSerializer
    queryset = TranslationRequest.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


# =====================================================
# TRANSLATION REQUEST CREATION
# =====================================================
class TranslationRequestCreateView(generics.CreateAPIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestCreateSerializer

    @require_token_and_plan(token_cost=7, min_plan="free", feature_name="Translation", cost_type="translation")
    def post(self, request, *args, **kwargs):
        subscription = request.subscription
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            consume_translation_token(subscription)
            translation = serializer.save(
                user=request.user,
                status="pending",
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "direction": translation.direction,
                "remaining_tokens": subscription.remaining_tokens(),
            },
            status=status.HTTP_201_CREATED,
        )


# =====================================================
# TEXT → SIGN (VIDEO)
# =====================================================


class TranslateToSignView(generics.GenericAPIView):
    """
    Text → Sign Language (Video)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TextToSignSerializer

    @require_token_and_plan(token_cost=10, min_plan="free", feature_name="Sign Generation")
    def post(self, request):
        subscription = request.subscription
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]

        # 1️⃣ Text → Gloss (AI)
        try:
            ai_result = asyncio.run(TranslationPipelineService.text_to_sign(text))
            gloss_tokens = ai_result["gloss"]
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 2️⃣ Gloss → Sign Video
        try:
            video_url = generate_sign_video_from_gloss(gloss_tokens)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 3️⃣ Save + Consume Tokens
        with transaction.atomic():
            consume_generation_token(subscription, amount=10)

            translation = TranslationRequest.objects.create(
                user=request.user,
                direction="to_sign",
                status="completed",
                input_text=text,
                output_video=video_url,
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "video": video_url,
                "remaining_tokens": subscription.remaining_tokens(),
            },
            status=status.HTTP_201_CREATED,
        )


# =====================================================
# 📺 YOUTUBE → SIGN LANGUAGE VIDEO
# =====================================================


class YouTubeTranslateView(APIView):
    """
    YouTube URL → Extract Audio → Speech-to-Text → Text-to-Sign → Sign Video
    """
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=15, min_plan="basic", feature_name="YouTube Translation")
    def post(self, request):
        youtube_url = request.data.get("youtube_url")
        if not youtube_url:
            return Response(
                {"detail": _("YouTube URL is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = request.subscription

        # 1️⃣ Download audio from YouTube
        try:
            audio_path = download_youtube_audio(youtube_url)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2️⃣ Speech-to-Text (extract spoken text)
        wav_path = None
        try:
            # Convert to WAV using ffmpeg
            wav_path = audio_path.replace(".mp3", ".wav")
            subprocess.run(
                ["ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
                capture_output=True,
                timeout=30,
            )

            with open(wav_path, "rb") as f:
                wav_data = f.read()

            # Call STT service
            stt_client = SpeechToTextClient()
            files = {"file": ("audio.wav", wav_data, "audio/wav")}
            data = {"language": "ar", "task": "transcribe"}

            response = httpx.post(
                stt_client.base_url + "/",
                files=files,
                data=data,
                timeout=60,
            )
            response.raise_for_status()
            transcribed_text = response.json().get("text", "")

            if not transcribed_text:
                return Response(
                    {"detail": _("No speech detected in the video")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"detail": _("Failed to transcribe audio: ") + str(e)},
                status=status.HTTP_500_INTERNAL_ERROR,
            )
        finally:
            # Cleanup temp files
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)

        # 3️⃣ Text-to-Sign (generate sign language video)
        try:
            ai_result = asyncio.run(TranslationPipelineService.text_to_sign(transcribed_text))
            gloss_tokens = ai_result["gloss"]

            video_url = generate_sign_video_from_gloss(gloss_tokens)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4️⃣ Save + Consume Tokens
        with transaction.atomic():
            consume_generation_token(subscription, amount=15)

            translation = TranslationRequest.objects.create(
                user=request.user,
                direction="youtube_to_sign",
                input_type="youtube_url",
                input_text=youtube_url,
                output_type="video",
                output_text=transcribed_text,
                output_video=video_url,
                status="completed",
                tokens_used=15,
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "transcribed_text": transcribed_text,
                "video": video_url,
                "remaining_tokens": subscription.remaining_tokens(),
            },
            status=status.HTTP_201_CREATED,
        )
class UnityTranslateView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
        request=TextToSignSerializer,
        responses={200: UnitySignResponseSerializer},
        summary="Translate text to Unity Animations",
        description="Receives text (Arabic/English) and translates it to animation trigger names used by the Unity WebGL player."
    )
    def post(self, request):

        text = request.data.get("text", "")

        logger.info("=" * 50)
        logger.info("UNITY SIGN REQUEST")
        logger.info("=" * 50)
        logger.info("USER INPUT   : %r", text)

        if not text or not text.strip():
            logger.warning("[UnitySign] Empty input received.")
            empty = {"animations": [], "unknown_words": [], "source": "error"}
            logger.info("FINAL RESP   : %s  (empty input)", empty)
            logger.info("=" * 50)
            return Response(empty)

        # 1️⃣ Try NLP text-to-gloss first
        try:
            logger.info("[UnitySign] Calling NLP text-to-gloss ...")
            ai_result = asyncio.run(
                asyncio.wait_for(
                    TranslationPipelineService._text_to_gloss_client.text_to_gloss(text),
                    timeout=settings.AI_TIMEOUT,
                )
            )

            logger.info("AI RAW RESULT: %s", ai_result)

            raw = (
                ai_result.get("gloss_translation")
                or ai_result.get("gloss")
                or ai_result.get("text")
                or text
            )

            logger.info("MODEL OUTPUT : %r", raw)

            result = translate_to_animation_names(str(raw))
            result["source"] = "nlp"

            logger.info("ANIMATIONS   : %s", result["animations"])
            logger.info("UNKNOWN WORDS: %s", result["unknown_words"])
            logger.info("SOURCE       : nlp")
            logger.info("FINAL RESP   : %s", result)
            logger.info("=" * 50)

            return Response(result)

        except asyncio.TimeoutError:
            logger.warning("[UnitySign] NLP timed out (AI_TIMEOUT=%s s), falling back ...", settings.AI_TIMEOUT)

        except Exception as e:
            logger.warning("[UnitySign] NLP failed: %s: %s", type(e).__name__, e)

        # 2️⃣ Fallback: Unity SignMatcher
        logger.info("FALLBACK     : trying Unity SignMatcher")
        from .services.unity_sign_matcher_client import UnitySignMatcherClient
        client = UnitySignMatcherClient()
        animations = asyncio.run(client.match(text))

        logger.info("SIGN MATCHER : %s", animations)

        if animations:
            fallback_resp = {
                "animations": animations,
                "unknown_words": [],
                "source": "unity_matcher",
            }
            logger.info("FINAL RESP   : %s", fallback_resp)
            logger.info("=" * 50)
            return Response(fallback_resp)

        # 3️⃣ Last resort: direct ANIMATION_MAP lookup
        logger.info("FALLBACK     : trying direct ANIMATION_MAP lookup")
        logger.info("MAP INPUT    : words = %s", text.split())

        # Log each word lookup so we can see what's missing from the map
        for word in text.split():
            if word in ANIMATION_MAP:
                logger.info("MAP HIT      : %r -> %r", word, ANIMATION_MAP[word])
            else:
                logger.warning("MAP MISS     : %r not found in ANIMATION_MAP", word)

        result = translate_to_animation_names(text)
        result["source"] = "sign_map"

        logger.info("ANIMATIONS   : %s", result["animations"])
        logger.info("UNKNOWN WORDS: %s", result["unknown_words"])
        logger.info("SOURCE       : sign_map")
        logger.info("FINAL RESP   : %s", result)
        logger.info("=" * 50)

        return Response(result)


# =====================================================
# HYBRID TRANSLATION PIPELINE
# =====================================================
class TranslationAPIView(APIView):
    """
    Hybrid Translation Endpoint
    POST /api/v1/translation/translate/
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        text = request.data.get("text", "").strip()
        
        if not text:
            return Response(
                {"success": False, "error": "Text is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        logger.info("Translation request received for text: '%s'", text)
        
        normalized_text = normalize_arabic_text(text)
        
        # Step 1: Check Cache
        cached_result = get_cached_translation(normalized_text)
        if cached_result:
            cached_result['source'] = 'cache'
            return Response(cached_result, status=status.HTTP_200_OK)
            
        # Step 2: Call AI Service
        ai_result = call_ai_translation(text)
        
        if ai_result:
            # Step 3: AI success -> Save to cache and return
            set_cached_translation(normalized_text, ai_result)
            return Response(ai_result, status=status.HTTP_200_OK)
            
        # Step 4: AI failed/timeout -> Fallback to Sign Matcher
        try:
            fallback_result = match_sign(text)
            return Response(fallback_result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Sign Matcher failed for text: %s. Error: %s", text, e)
            return Response(
                {"success": False, "error": "Unable to translate text"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )