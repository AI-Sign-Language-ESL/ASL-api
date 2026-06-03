import asyncio
import logging
import os
import subprocess
import time
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
    TextToSignSerializer,
    TranslationRequestCreateSerializer,
    TranslationRequestStatusSerializer,
    SignLanguageConfigSerializer,
    TranslationRequestListSerializer,
    UnitySignResponseSerializer,
)
from .services.youtube_service import (
    download_youtube_audio,
    get_youtube_video_info,
    calculate_youtube_token_cost,
)

from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
from tafahom_api.apps.v1.billing.services import consume_translation_token, consume_generation_token, consume_history_save_token
from tafahom_api.common.decorators import require_token_and_plan
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
from tafahom_api.apps.v1.translation.services.sign_matcher_service import match_sign, normalize_arabic_text
from tafahom_api.apps.v1.translation.services.cache_service import get_cached_translation, set_cached_translation
from tafahom_api.apps.v1.translation.services.ai_service import call_ai_translation

logger = logging.getLogger(__name__)


# =====================================================
# SPEECH → TEXT
# =====================================================
class SpeechToTextView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=2, min_plan="basic", feature_name="Speech Mode", cost_type="speech_to_text")
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
                subscription.consume(2)

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

    @require_token_and_plan(token_cost=7, min_plan="free", feature_name="Sign Generation")
    def post(self, request):
        subscription = request.subscription
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]

        # 1️⃣ Text → Sign (sign-map + NLP fallback)
        try:
            ai_result = asyncio.run(SignTranslationService.text_to_sign(text))
            video_url = ai_result["video"]
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 2️⃣ Save + Consume Tokens
        with transaction.atomic():
            consume_generation_token(subscription)

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

    def post(self, request):
        youtube_url = request.data.get("youtube_url")
        if not youtube_url:
            return Response(
                {"detail": _("YouTube URL is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 0️⃣ Get video info for token cost calculation
        try:
            video_info = get_youtube_video_info(youtube_url)
            token_cost = calculate_youtube_token_cost(video_info["duration"])
        except ValueError as e:
            # Fall back to default cost if info fetch fails
            token_cost = 12

        subscription = getattr(request.user, "subscription", None)
        if not subscription:
            return Response(
                {"detail": _("No active subscription found.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan_rank = {"free": 0, "basic": 1, "go": 2, "enterprise": 3}
        if plan_rank.get(subscription.plan.plan_type, 0) < plan_rank.get("basic", 0):
            return Response(
                {"detail": _("YouTube Translation is available on BASIC plans and above.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not subscription.can_consume(token_cost):
            return Response(
                {"detail": _(f"Not enough tokens. YouTube Translation requires {token_cost} tokens.")},
                status=status.HTTP_403_FORBIDDEN,
            )

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
            # Cleanup temp files and their parent directories completely
            if audio_path and os.path.exists(audio_path):
                import shutil
                output_dir = os.path.dirname(audio_path)
                try:
                    shutil.rmtree(output_dir)
                except Exception as e:
                    logger.error("Failed to clean up temp dir %s: %s", output_dir, e)

        # 3️⃣ Text-to-Sign (sign-map + NLP fallback)
        try:
            ai_result = asyncio.run(SignTranslationService.text_to_sign(transcribed_text))
            video_url = ai_result["video"]
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_ERROR,
            )

        # 4️⃣ Save + Consume Tokens
        with transaction.atomic():
            subscription.consume(token_cost)

            translation = TranslationRequest.objects.create(
                user=request.user,
                direction="youtube_to_sign",
                input_type="youtube_url",
                input_text=youtube_url,
                output_type="video",
                output_text=transcribed_text,
                output_video=video_url,
                status="completed",
                tokens_used=token_cost,
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "transcribed_text": transcribed_text,
                "video": video_url,
                "remaining_tokens": subscription.remaining_tokens(),
                "tokens_used": token_cost,
            },
            status=status.HTTP_201_CREATED,
        )
class UnityTranslateView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TextToSignSerializer,
        responses={200: UnitySignResponseSerializer},
        summary="Translate text to Unity Animations",
        description="Receives text (Arabic/English) and translates it to animation trigger names used by the Unity WebGL player."
    )
    @require_token_and_plan(
        token_cost=10, min_plan="free", feature_name="Sign Generation"
    )
    def post(self, request):

        subscription = request.subscription
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

        # Phase 1: Direct ANIMATION_MAP lookup first — never send known words to NLP
        result = translate_to_animation_names(text)
        source_parts = ["sign_map"] if result["animations"] else []
        logger.info("PHASE 1 (sign map): animations=%s unknown=%s", result["animations"], result["unknown_words"])

        # Phase 2: NLP only on words the sign map could NOT match
        if result["unknown_words"]:
            unknown_text = " ".join(result["unknown_words"])
            logger.info("PHASE 2 (NLP on unknowns): %r", unknown_text)
            try:
                nlp_timeout = min(getattr(settings, 'AI_TIMEOUT', 30), 10)
                t2g_client = TextToGlossClient()
                ai_result = asyncio.run(
                    asyncio.wait_for(
                        t2g_client.text_to_gloss(unknown_text),
                        timeout=nlp_timeout,
                    )
                )
                logger.info("NLP RAW OUTPUT: %s", ai_result)
                raw = (
                    ai_result.get("gloss_translation")
                    or ai_result.get("gloss")
                    or ai_result.get("text")
                    or ""
                )
                if raw.strip():
                    nlp_matched = translate_to_animation_names(str(raw))
                    if nlp_matched["animations"]:
                        result["animations"].extend(nlp_matched["animations"])
                        source_parts.append("nlp")
                        logger.info("NLP added animations: %s", nlp_matched["animations"])
                    result["unknown_words"] = nlp_matched["unknown_words"]
            except asyncio.TimeoutError:
                logger.warning("NLP timed out after %ss, skipping", nlp_timeout)
            except Exception as e:
                logger.warning("NLP failed: %s: %s", type(e).__name__, e)

        # Phase 3: Unity SignMatcher for remaining unknowns
        if not result["animations"] and result["unknown_words"]:
            logger.info("PHASE 3 (Unity SignMatcher): %r", result["unknown_words"])
            try:
                from .services.unity_sign_matcher_client import UnitySignMatcherClient
                client = UnitySignMatcherClient()
                animations = asyncio.run(client.match(" ".join(result["unknown_words"])))
                logger.info("SIGN MATCHER : %s", animations)
                if animations:
                    result["animations"].extend(animations)
                    source_parts.append("unity_matcher")
            except Exception as e:
                logger.warning("SignMatcher failed: %s", e)

        result["source"] = "+".join(source_parts) if source_parts else "none"

        with transaction.atomic():
            consume_generation_token(subscription)
        result["remaining_tokens"] = subscription.remaining_tokens()
        logger.info("TOKENS       : consumed 10, %s remaining", result["remaining_tokens"])
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
            # Cache the fallback result so the next click is instant
            set_cached_translation(normalized_text, fallback_result)
            return Response(fallback_result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Sign Matcher failed for text: %s. Error: %s", text, e)
            return Response(
                {"success": False, "error": "Unable to translate text"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =====================================================
# 🧪 TEST GLOSS — NLP Pipeline Tester
# =====================================================


class TestGlossView(APIView):
    """
    Temporary testing endpoint for the NLP gloss-to-text pipeline.

    POST /api/v1/sign-language/test-gloss/

    Sends a gloss to the NLP model and returns the Arabic translation.
    Used to test the complete translation pipeline before the Computer Vision
    model is available.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        gloss = request.data.get("gloss", "").strip()

        if not gloss:
            return Response(
                {"error": "Gloss text must not be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("=" * 60)
        logger.info("TEST GLOSS REQUEST")
        logger.info("=" * 60)
        logger.info("Input gloss: %r", gloss)

        from tafahom_api.apps.v1.ai.clients.nlp_model_client import NLPModelClient
        
        try:
            client = NLPModelClient()
            result = asyncio.run(client.translate_gloss(gloss))
            
            logger.info("NLP translation result: %r", result.text)
            logger.info("=" * 60)

            return Response(
                {
                    "gloss": gloss,
                    "translation": result.text,
                    "winner_model": result.raw.get("winner_model"),
                    "latency_ms": result.raw.get("latency_ms"),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error("NLP service failed: %s", e)
            logger.info("=" * 60)
            return Response(
                {
                    "gloss": gloss,
                    "error": f"NLP service failed: {e}",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


# =====================================================
# 📜 SAVE TRANSLATION TO HISTORY
# =====================================================


class SaveTranslationHistoryView(APIView):
    """
    Save a translation request to user history (Basic+ plans, 2 tokens).
    POST /api/v1/translation/requests/<id>/save/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        subscription = getattr(user, "subscription", None)
        if not subscription:
            return Response(
                {"detail": _("No active subscription found.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan_rank = {"free": 0, "basic": 1, "go": 2, "enterprise": 3}
        if plan_rank.get(subscription.plan.plan_type, 0) < plan_rank.get("basic", 0):
            return Response(
                {"detail": _("History save is available on BASIC plans and above.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not subscription.can_consume(2):
            return Response(
                {"detail": _("Not enough tokens. Saving to history requires 2 tokens.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            translation = TranslationRequest.objects.get(pk=pk, user=user)
        except TranslationRequest.DoesNotExist:
            return Response(
                {"detail": _("Translation request not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if translation.saved:
            return Response(
                {"detail": _("Translation already saved to history.")},
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            consume_history_save_token(subscription)
            translation.saved = True
            translation.save(update_fields=["saved"])

        return Response(
            {
                "detail": _("Translation saved to history."),
                "id": translation.id,
                "remaining_tokens": subscription.remaining_tokens(),
            },
            status=status.HTTP_200_OK,
        )

# =====================================================
# 🧪 MOCK CV ENDPOINT (Phase 7 Test Mode)
# =====================================================

class MockCVEndpointView(APIView):
    """
    Mock CV Endpoint for testing the Translation Pipeline.
    POST /api/v1/translation/mock-cv/
    
    Returns the mocked gloss payload.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {"gloss": "سبب رغبه شراء"},
            status=status.HTTP_200_OK
        )