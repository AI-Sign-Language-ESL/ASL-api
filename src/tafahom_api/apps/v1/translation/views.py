import asyncio
import logging

from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TranslationRequest, SignLanguageConfig
from .serializers import (
    TranslationRequestCreateSerializer,
    TranslationRequestStatusSerializer,
    SignLanguageConfigSerializer,
    TranslationRequestListSerializer,
)

from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
from tafahom_api.apps.v1.billing.services import consume_translation_token, consume_generation_token
from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)
from tafahom_api.apps.v1.translation.services.streaming_translation_service import (
    TranslationPipelineService,
)
from tafahom_api.apps.v1.translation.serializers import TextToSignSerializer

from tafahom_api.common.decorators import require_token_and_plan

logger = logging.getLogger(__name__)


# =====================================================
# SPEECH → TEXT
# =====================================================
class SpeechToTextView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    @require_token_and_plan(token_cost=5, min_plan="basic", feature_name="Speech Mode")
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

    @require_token_and_plan(token_cost=7, min_plan="free", feature_name="Translation")
    def post(self, request, *args, **kwargs):
        subscription = request.subscription
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            consume_translation_token(subscription, amount=7)
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
