import asyncio

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.parsers import MultiPartParser, FormParser

from .models import TranslationRequest, SignLanguageConfig
from .serializers import (
    TranslationRequestCreateSerializer,
    TranslationRequestStatusSerializer,
    SignLanguageConfigSerializer,
    TranslationRequestListSerializer,
)

from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
from tafahom_api.apps.v1.billing.services import consume_translation_credit

from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)

from tafahom_api.apps.v1.translation.services.streaming_translation_service import (
    TranslationPipelineService,
)

from rest_framework.views import APIView

from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from asgiref.sync import async_to_sync

# =====================================================
# HELPERS
# =====================================================
import logging


logger = logging.getLogger(__name__)


class SpeechToTextView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        audio_file = request.FILES.get("file")

        if not audio_file:
            return Response(
                {"error": "No audio file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔥 HARD GUARD: reject silence / too short audio
        if audio_file.size < 25_000:  # ~0.8s @ 16kHz PCM16
            logger.error(
                "STT: audio too small (%s bytes) — rejecting",
                audio_file.size,
            )
            return Response(
                {"text": ""},
                status=status.HTTP_200_OK,
            )

        client = SpeechToTextClient()

        try:
            result = async_to_sync(client.speech_to_text)(audio_file)
        except Exception as e:
            logger.exception("STT CLIENT ERROR")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.error("RAW STT RESULT TYPE: %s", type(result))
        logger.error("RAW STT RESULT VALUE: %s", result)

        if not isinstance(result, dict):
            return Response(
                {"error": f"Invalid STT result: {result}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        text = result.get("text", "")
        if isinstance(text, str):
            text = text.strip()
        else:
            text = ""

        logger.error("FINAL EXTRACTED TEXT: %r", text)

        return Response(
            {"text": text},
            status=status.HTTP_200_OK,
        )


def _get_or_create_wallet(user):
    """
    Ensure the user has a subscription wallet.
    """
    try:
        return user.subscription
    except ObjectDoesNotExist:
        free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
        if not free_plan:
            free_plan = SubscriptionPlan.objects.filter(is_active=True).first()

        if not free_plan:
            return None

        return Subscription.objects.create(
            user=user,
            plan=free_plan,
            status="active",
            billing_period="monthly",
            credits_used=0,
            bonus_credits=0,
        )


# =====================================================
# VIEWS
# =====================================================


class SignLanguageListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignLanguageConfigSerializer
    queryset = SignLanguageConfig.objects.all().order_by("id")


class TranslationRequestCreateView(generics.CreateAPIView):
    """
    Generic translation request creation (any direction).
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestCreateSerializer

    def post(self, request, *args, **kwargs):
        subscription = _get_or_create_wallet(request.user)
        if not subscription:
            return Response(
                {
                    "detail": "System Configuration Error: No subscription plans available."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not subscription.can_consume(1):
            return Response(
                {"detail": "Not enough credits"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            consume_translation_credit(subscription)
            translation = serializer.save(
                user=request.user,
                status="pending",
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "direction": translation.direction,
                "remaining_credits": subscription.remaining_credits(),
            },
            status=status.HTTP_201_CREATED,
        )


class MyTranslationRequestsView(generics.ListAPIView):
    """
    List translation history for the authenticated user.
    """

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
# TEXT → SIGN (VIDEO)
# =====================================================


class TranslateToSignView(generics.GenericAPIView):
    """
    Text → Sign Language (Video).

    Pipeline:
    Text
    → Arabic Gloss AI (text_to_gloss)
    → Arabic gloss tokens
    → Gloss → Video mapping
    → FFmpeg
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestCreateSerializer

    def post(self, request):
        subscription = _get_or_create_wallet(request.user)
        if not subscription:
            return Response(
                {"detail": "System Configuration Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not subscription.can_consume(1):
            return Response(
                {"detail": "Not enough credits"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data.get("text")

        # -------------------------------------------------
        # 1️⃣ AI: Text → Arabic Gloss
        # -------------------------------------------------
        try:
            ai_result = asyncio.run(TranslationPipelineService.text_to_sign(text))
            gloss_tokens = ai_result.get("gloss")
        except Exception:
            return Response(
                {"detail": "Failed to generate gloss from text"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # -------------------------------------------------
        # 2️⃣ Gloss → Sign Video (FFmpeg)
        # -------------------------------------------------
        try:
            video_url = generate_sign_video_from_gloss(gloss_tokens)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # 3️⃣ Save + Consume Credit
        # -------------------------------------------------
        with transaction.atomic():
            consume_translation_credit(subscription)

            translation = serializer.save(
                user=request.user,
                direction="to_sign",
                status="completed",
                output_url=video_url,
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "video": video_url,
                "remaining_credits": subscription.remaining_credits(),
            },
            status=status.HTTP_201_CREATED,
        )
