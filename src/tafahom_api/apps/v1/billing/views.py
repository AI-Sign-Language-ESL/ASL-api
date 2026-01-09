from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from django.utils import timezone
from datetime import timedelta

from . import models, serializers


class SubscriptionPlanListView(generics.ListAPIView):
    queryset = models.SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = serializers.SubscriptionPlanSerializer


class MySubscriptionView(generics.RetrieveAPIView):
    serializer_class = serializers.SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Defensive: Use get_or_create to prevent "RelatedObjectDoesNotExist"
        # crashes if the post_save signal failed or didn't run for old users.

        # 1. Try to fetch existing subscription
        try:
            return self.request.user.subscription
        except models.Subscription.DoesNotExist:
            pass

        # 2. If missing, create a default "Free" wallet dynamically
        # (This matches the logic in dataset/views.py and users/signals.py)
        free_plan = models.SubscriptionPlan.objects.filter(plan_type="free").first()

        if not free_plan:
            # Fallback: Just grab the first active plan if 'free' specific type is missing
            free_plan = models.SubscriptionPlan.objects.filter(is_active=True).first()

        subscription = models.Subscription.objects.create(
            user=self.request.user,
            plan=free_plan,
            status="active",
            billing_period="monthly",
            credits_used=0,
            bonus_credits=0,
        )
        return subscription


class SubscribeView(generics.CreateAPIView):
    serializer_class = serializers.SubscribeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Override create to return the Subscription data instead of just the input data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 1. Validate Plan
        plan = get_object_or_404(
            models.SubscriptionPlan, id=serializer.validated_data["plan_id"]
        )

        billing_period = serializer.validated_data["billing_period"]

        # 2. Calculate End Date
        end_date = timezone.now() + (
            timedelta(days=365) if billing_period == "yearly" else timedelta(days=30)
        )

        # 3. Update or Create Subscription
        # We use update_or_create to handle upgrading/downgrading seamlessly
        subscription, created = models.Subscription.objects.update_or_create(
            user=self.request.user,
            defaults={
                "plan": plan,
                "billing_period": billing_period,
                "end_date": end_date,
                "status": "active",
                # Note: We do NOT reset credits_used or bonus_credits here
                # because user might be just switching billing cycles.
                # Resetting is handled by the model's 'reset_if_needed' logic or a separate task.
            },
        )

        # 4. Return the full subscription object
        response_serializer = serializers.SubscriptionSerializer(subscription)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=None,
    responses={200: None},
)
class CancelSubscriptionView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request):
        # Handle case where subscription might not exist yet
        try:
            subscription = request.user.subscription
            subscription.status = "cancelled"
            subscription.save(update_fields=["status"])
        except models.Subscription.DoesNotExist:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Subscription cancelled"},
            status=status.HTTP_200_OK,
        )
