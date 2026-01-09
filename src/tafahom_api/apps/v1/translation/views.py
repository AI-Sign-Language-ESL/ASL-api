from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from .models import TranslationRequest
from .serializers import (
    TranslationRequestCreateSerializer,
    TranslationRequestStatusSerializer,
)

# Import Billing models for defensive wallet creation
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
from tafahom_api.apps.v1.billing.services import consume_translation_credit


class TranslateToSignView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestCreateSerializer

    def post(self, request):
        # 🛡️ DEFENSIVE: Get or Create Subscription (Wallet)
        # This prevents crashes if the registration signal failed for any reason.
        try:
            subscription = request.user.subscription
        except ObjectDoesNotExist:
            # Auto-create free wallet if missing
            free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
            if not free_plan:
                # Fallback to any active plan to keep system running
                free_plan = SubscriptionPlan.objects.filter(is_active=True).first()

            if not free_plan:
                return Response(
                    {
                        "detail": "System Configuration Error: No subscription plans available."
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            subscription = Subscription.objects.create(
                user=request.user,
                plan=free_plan,
                status="active",
                billing_period="monthly",
                credits_used=0,
                bonus_credits=0,
            )

        # 1. Check Credits
        if not subscription.can_consume(1):
            return Response(
                {"detail": "Not enough credits"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Atomic Transaction: Consume Credit + Save Request
        with transaction.atomic():
            consume_translation_credit(subscription)

            translation = serializer.save(
                user=request.user,
                direction="to_sign",
                status="completed",  # Mocked for MVP
                # output_video="mock_output.mp4", # Optional: can leave null
            )

        return Response(
            {
                "id": translation.id,
                "status": translation.status,
                "remaining_credits": subscription.remaining_credits(),
            },
            status=status.HTTP_201_CREATED,
        )


class TranslationStatusView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TranslationRequestStatusSerializer
    queryset = TranslationRequest.objects.all()

    def get_queryset(self):
        # 🔐 Users can only see their own translations
        return super().get_queryset().filter(user=self.request.user)
