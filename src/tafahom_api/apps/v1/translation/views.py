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
    TextToSignSerializer,
)

from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
from tafahom_api.apps.v1.billing.services import consume_translation_credit

from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)

from tafahom_api.apps.v1.translation.services.streaming_translation_service import (
    TranslationPipelineService,
)

# =====================================================
# HELPERS
# =====================================================


def _get_or_create_wallet(user):
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

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


# =====================================================
# TEXT → SIGN (FINAL, CORRECT)
# =====================================================


class TranslateToSignView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TextToSignSerializer
    parser_classes = (MultiPartParser, FormParser)

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

        # 1️⃣ NLP: Text → Gloss
        try:
            ai_result = asyncio.run(TranslationPipelineService.text_to_sign(text))
            gloss_tokens = ai_result["gloss"]
        except Exception:
            return Response(
                {"detail": "Failed to generate gloss"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2️⃣ Gloss → Video
        try:
            video_url = generate_sign_video_from_gloss(gloss_tokens)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3️⃣ Save + Consume Credit
        with transaction.atomic():
            consume_translation_credit(subscription)

            translation = TranslationRequest.objects.create(
                user=request.user,
                direction="to_sign",
                input_type="text",
                output_type="video",
                input_text=text,
                status="completed",
                output_video=video_url,
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
