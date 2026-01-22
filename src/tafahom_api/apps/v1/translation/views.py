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
from tafahom_api.apps.v1.billing.services import consume_translation_credit
from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)
from tafahom_api.apps.v1.translation.services.streaming_translation_service import (
    TranslationPipelineService,
)
from tafahom_api.apps.v1.translation.serializers import TextToSignSerializer

logger = logging.getLogger(__name__)


# =====================================================
# SPEECH → TEXT
# =====================================================
class SpeechToTextView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
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

        logger.info("RAW STT RESULT: %s", result)

        if not isinstance(result, dict):
            logger.error("Invalid STT response type: %s", type(result))
            return Response(
                {"error": "Invalid STT response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        text = (result.get("text") or "").strip()

        if not text:
            logger.error(
                "STT returned EMPTY text — audio received but no transcript produced"
            )

        return Response({"text": text}, status=status.HTTP_200_OK)


# =====================================================
# SUBSCRIPTION WALLET
# =====================================================
def _get_or_create_wallet(user):
    try:
        return user.subscription
    except ObjectDoesNotExist:
        free_plan = (
            SubscriptionPlan.objects.filter(plan_type="free").first()
            or SubscriptionPlan.objects.filter(is_active=True).first()
        )

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

    def post(self, request, *args, **kwargs):
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


# =====================================================
# TEXT → SIGN (VIDEO)
# =====================================================


class TranslateToSignView(generics.GenericAPIView):
    """
    Text → Sign Language (Video)

    Pipeline:
    Arabic Text
    → Text-to-Gloss AI
    → Gloss tokens
    → Gloss → Video
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TextToSignSerializer

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

        text = serializer.validated_data["text"]

        # -------------------------------------------------
        # 1️⃣ Text → Gloss (AI)
        # -------------------------------------------------
        try:
            ai_result = asyncio.run(TranslationPipelineService.text_to_sign(text))
            gloss_tokens = ai_result.get("gloss")

            if not gloss_tokens:
                raise ValueError("Empty gloss result")

        except Exception as e:
            logger.exception("TEXT → GLOSS FAILED")
            return Response(
                {"detail": "Failed to generate gloss from text"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # -------------------------------------------------
        # 2️⃣ Gloss → Sign Video
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

            translation = TranslationRequest.objects.create(
                user=request.user,
                direction="to_sign",
                status="completed",
                input_text=text,
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
