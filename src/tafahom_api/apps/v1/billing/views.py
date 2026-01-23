from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from . import models, serializers


class SubscriptionPlanListView(generics.ListAPIView):
    serializer_class = serializers.SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return models.SubscriptionPlan.objects.filter(is_active=True)


class MySubscriptionView(generics.RetrieveAPIView):
    serializer_class = serializers.SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        subscription = getattr(self.request.user, "subscription", None)
        if subscription:
            return subscription

        free_plan = models.SubscriptionPlan.objects.filter(
            plan_type="free",
            is_active=True,
        ).first()

        if not free_plan:
            raise RuntimeError("No active subscription plans found.")

        return models.Subscription.objects.create(
            user=self.request.user,
            plan=free_plan,
            status="active",
            billing_period="monthly",
            credits_used=0,
            bonus_credits=0,
        )


class SubscribeView(generics.CreateAPIView):
    serializer_class = serializers.SubscribeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = get_object_or_404(
            models.SubscriptionPlan,
            id=serializer.validated_data["plan_id"],
            is_active=True,
        )

        billing_period = serializer.validated_data["billing_period"]

        end_date = timezone.now() + (
            timedelta(days=365) if billing_period == "yearly" else timedelta(days=30)
        )

        subscription, _ = models.Subscription.objects.update_or_create(
            user=request.user,
            defaults={
                "plan": plan,
                "billing_period": billing_period,
                "end_date": end_date,
                "status": "active",
            },
        )

        return Response(
            serializers.SubscriptionSerializer(subscription).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(request=None, responses={200: None})
class CancelSubscriptionView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        subscription = getattr(request.user, "subscription", None)

        if not subscription:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.status = "cancelled"
        subscription.save(update_fields=["status"])

        return Response(
            {"message": "Subscription cancelled"},
            status=status.HTTP_200_OK,
        )


class MyCreditsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UserCreditsSerializer

    def get(self, request):
        subscription = getattr(request.user, "subscription", None)

        if not subscription:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "total_credits": subscription.total_credits(),
            "credits_used": subscription.credits_used,
            "bonus_credits": subscription.bonus_credits,
            "remaining_credits": subscription.remaining_credits(),
            "can_consume": subscription.can_consume(),
        }

        return Response(data, status=status.HTTP_200_OK)
