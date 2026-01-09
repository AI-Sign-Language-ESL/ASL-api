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


# =====================================================
# HELPERS
# =====================================================


def _get_or_create_wallet(user):
    """
    Helper to ensure a user has a subscription wallet before processing payments.
    """
    try:
        return user.subscription
    except ObjectDoesNotExist:
        # Auto-create free wallet if missing
        free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
        if not free_plan:
            # Fallback to any active plan to keep system running
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
                {
                    "detail": "System Configuration Error: No subscription plans available."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2. Check Credits
        if not subscription.can_consume(1):
            return Response(
                {"detail": "Not enough credits"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 3. Validate Data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 4. Atomic Transaction: Consume Credit + Save Request
        with transaction.atomic():
            consume_translation_credit(subscription)

            # Save with user and pending status
            translation = serializer.save(user=request.user, status="pending")

        # 5. Return Response
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
    Lists translation history for the authenticated user.
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
        # 🔐 Users can only see their own translations
        return super().get_queryset().filter(user=self.request.user)


# =====================================================
# LEGACY / SPECIFIC VIEWS
# =====================================================


class TranslateToSignView(generics.GenericAPIView):
    """
    Specific endpoint for Text -> Sign.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestCreateSerializer

    def post(self, request):
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
                direction="to_sign",
                status="completed",  # Mocked for MVP
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "remaining_credits": subscription.remaining_credits(),
            },
            status=status.HTTP_201_CREATED,
        )
