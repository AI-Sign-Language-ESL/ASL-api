from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import asyncio

from .models import YouTubeTranslation
from .serializers import (
    YouTubeTranslationSerializer,
    YouTubeTranslationCreateSerializer,
    VideoUploadSerializer,
    BrowserTranscriptSerializer,
    TranscriptFetchSerializer,
)
from .services.browser_transcript import process_browser_transcript
from .services.translation import start_youtube_translation
from .services.extraction import fetch_transcript_with_segments
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
from tafahom_api.apps.v1.translation.services.sign_translation_service import normalize_arabic
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
from asgiref.sync import async_to_sync

from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient
from rest_framework.parsers import MultiPartParser, FormParser

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

        # Step 1: Use pre-supplied transcript if available (from browser extension)
        transcript = request.data.get("transcript", "").strip()
        source = "browser"

        if not transcript or len(transcript) <= 10:
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
                TextToGlossClient().text_to_gloss
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


class TranscriptCheckView(APIView):
    """
    Quick YouTube access probe.
    Returns 403 immediately if YouTube is blocked.
    React uses this to decide whether to show upload fallback.
    """
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=0, min_plan="basic", feature_name="YouTube Translation")
    def post(self, request):
        url = request.data.get("url") or request.data.get("video_id")
        if not url:
            return Response({"available": False, "error": "No URL provided"}, status=status.HTTP_400_BAD_REQUEST)

        video_id = _extract_video_id(url) if not _is_video_id(url) else url
        if not video_id:
            return Response({"available": False, "error": "Invalid video ID"}, status=status.HTTP_400_BAD_REQUEST)

        # Quick probe: try youtube-transcript-api with short timeout
        try:
            import httpx
            resp = httpx.get(
                f"https://www.youtube.com/watch?v={video_id}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=5,
                follow_redirects=True,
            )
            if resp.status_code != 200 or len(resp.content) < 1000:
                logger.warning(f"YouTube probe returned {resp.status_code}, content length: {len(resp.content)}")
                return Response(
                    {"available": False, "blocked": True, "error": "YouTube access blocked"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if response contains caption data
            has_captions = 'captionTracks' in resp.text or 'playerCaptionsTracklistRenderer' in resp.text
            if not has_captions:
                return Response(
                    {"available": True, "has_captions": False, "message": "Video has no caption tracks"},
                    status=status.HTTP_200_OK,
                )

            # Try to get the actual transcript
            try:
                transcript, source = extract_transcript(f"https://youtube.com/watch?v={video_id}")
                if transcript and len(transcript) >= 10:
                    return Response({
                        "available": True,
                        "has_captions": True,
                        "transcript": transcript,
                    })
                return Response({
                    "available": True,
                    "has_captions": True,
                    "transcript_empty": True,
                    "message": "Transcript was empty",
                })
            except Exception as e:
                logger.warning(f"Transcript fetch failed during probe: {e}")
                return Response({"available": True, "has_captions": True, "fetch_failed": True})

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(f"YouTube probe connection error: {e}")
            return Response(
                {"available": False, "blocked": True, "error": "YouTube access blocked"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.warning(f"YouTube probe failed: {e}")
            return Response(
                {"available": False, "blocked": True, "error": "YouTube access blocked"},
                status=status.HTTP_403_FORBIDDEN,
            )


class ProcessTranscriptView(APIView):
    """
    Accepts pre-extracted transcript from the browser extension.
    Runs NLP → Gloss → Animation pipeline synchronously (same as unity-sign).
    Does NOT call extract_transcript(), YouTubeTranscriptApi, or yt-dlp.
    """
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=10, min_plan="basic", feature_name="YouTube Translation")
    def post(self, request):
        transcript = request.data.get("transcript", "").strip()
        video_id = request.data.get("video_id", "")
        title = request.data.get("title", "")
        source = request.data.get("source", "transcript_panel")
        language = request.data.get("language", "")
        segments = request.data.get("segments", [])

        logger.info("=" * 50)
        logger.info("PROCESS TRANSCRIPT (YouTube Extension)")
        logger.info("=" * 50)
        logger.info("Transcript length: %s chars", len(transcript))
        logger.info("Source          : %s", source)
        logger.info("Segments        : %s", len(segments))
        logger.info("Video ID        : %s", video_id)
        logger.info("Language        : %s", language)

        if not transcript or len(transcript) < 5:
            return Response(
                {"success": False, "error": "Transcript is too short or empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = request.subscription
        if not subscription.can_consume(10):
            return Response(
                {"success": False, "requires_upload": True, "error": "Not enough tokens."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Phase 1: Direct ANIMATION_MAP lookup first — never send known words to NLP
        result = translate_to_animation_names(transcript)
        source_parts = ["sign_map"] if result["animations"] else []
        logger.info("PHASE 1 (sign map): animations=%s unknown=%s", result["animations"], result["unknown_words"])

        # Phase 2: NLP only on words that the sign map could NOT match
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
                    # Match NLP output against sign map
                    nlp_matched = translate_to_animation_names(str(raw))
                    if nlp_matched["animations"]:
                        result["animations"].extend(nlp_matched["animations"])
                        source_parts.append("nlp")
                        logger.info("NLP added animations: %s", nlp_matched["animations"])
                    result["unknown_words"] = nlp_matched["unknown_words"]
                else:
                    logger.warning("NLP returned empty output")
            except asyncio.TimeoutError:
                logger.warning("NLP timed out after %ss, skipping", nlp_timeout)
            except Exception as e:
                logger.warning("NLP failed: %s: %s", type(e).__name__, e)

        # Phase 3: Fallback — Unity SignMatcher for remaining unknowns
        if not result["animations"] and result["unknown_words"]:
            logger.info("PHASE 3 (Unity SignMatcher): %r", result["unknown_words"])
            try:
                from tafahom_api.apps.v1.translation.services.unity_sign_matcher_client import UnitySignMatcherClient
                client = UnitySignMatcherClient()
                animations = asyncio.run(client.match(" ".join(result["unknown_words"])))
                logger.info("SIGN MATCHER : %s", animations)
                if animations:
                    result["animations"].extend(animations)
                    source_parts.append("unity_matcher")
            except Exception as e:
                logger.warning("SignMatcher failed: %s", e)

        result["source"] = "+".join(source_parts) if source_parts else "none"

        # Save record and consume tokens
        with transaction.atomic():
            subscription.consume(10)
            translation = YouTubeTranslation.objects.create(
                user=request.user,
                youtube_url=f"https://youtube.com/watch?v={video_id}" if video_id else "",
                video_id=video_id,
                title=title,
                transcript=transcript,
                source=source,
                segments=segments,
                language=language,
                status="completed",
                tokens_used=10,
                animation_data=result.get("animations", []),
            )

        result["translation_id"] = translation.id
        result["transcript"] = transcript
        result["tokens_used"] = 10
        result["remaining_tokens"] = subscription.remaining_tokens()

        logger.info("FINAL RESP   : %s", result)
        logger.info("=" * 50)
        return Response(result)



class BrowserTranscriptView(APIView):
    """
    Accepts transcript text extracted in the user's browser.
    Runs NLP → Gloss → Sign Translation synchronously and returns the full result.
    No YouTube fetch is attempted from the server.
    """
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=0, min_plan="basic", feature_name="YouTube Translation")
    def post(self, request):
        serializer = BrowserTranscriptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transcript = serializer.validated_data["transcript"]
        video_id = serializer.validated_data.get("video_id", "")
        title = serializer.validated_data.get("title", "")
        language = serializer.validated_data.get("language", "ar")

        subscription = request.subscription
        if not subscription or not subscription.can_consume(10):
            return Response(
                {"success": False, "error": "Not enough tokens. YouTube translation requires 10 tokens."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            result = process_browser_transcript(
                transcript=transcript,
                user=request.user,
                video_id=video_id,
                title=title,
                language=language,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Browser transcript processing failed: {e}")
            return Response(
                {"success": False, "error": "Translation processing failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _extract_video_id(url):
    import re
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&#]|$)", url)
    return match.group(1) if match else None


def _is_video_id(value):
    import re
    return bool(re.match(r"^[0-9A-Za-z_-]{11}$", value))


class FetchTranscriptView(APIView):
    """
    POST /api/v1/youtube/transcript/fetch/
    Accepts video_id, fetches transcript server-side using youtube-transcript-api.
    Falls back to yt-dlp + Whisper if no captions available.
    Returns timestamped transcript segments.
    """
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=0, min_plan="basic", feature_name="YouTube Translation")
    def post(self, request):
        serializer = TranscriptFetchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        video_id = serializer.validated_data["video_id"]
        language = serializer.validated_data.get("language")
        logger.info(f"Fetching transcript for video_id: {video_id} (lang: {language or 'auto'})")

        try:
            result = fetch_transcript_with_segments(video_id, preferred_lang=language)

            if result["success"]:
                return Response(result, status=status.HTTP_200_OK)

            logger.warning(f"Transcript fetch failed for {video_id}: {result.get('error')}")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.exception(f"Transcript fetch error for {video_id}: {e}")
            return Response(
                {"success": False, "error": "Failed to fetch transcript. Please try uploading the video file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class YouTubeUploadVideoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VideoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        video_file = serializer.validated_data.get("video") or serializer.validated_data.get("video_file")
        if not video_file:
            return Response(
                {"success": False, "error": "No video file provided. Use field 'video' or 'video_file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stt_client = SpeechToTextClient()
            stt_resp = async_to_sync(stt_client.speech_to_text)(video_file)
            transcript = (stt_resp.get("text") or "").strip()

            if not transcript:
                return Response(
                    {"success": False, "error": "Speech recognition returned empty transcript."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response({
                "success": True,
                "source": "upload",
                "transcript": transcript,
            })

        except Exception as e:
            logger.exception(f"Upload video processing failed: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
