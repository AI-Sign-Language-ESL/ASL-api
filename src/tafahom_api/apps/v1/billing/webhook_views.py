from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from django.utils import timezone
from django.db import transaction

from .models import Subscription, PaymentTransaction, SubscriptionPlan
from tafahom_api.apps.v1.users.models import User


class PaymentWebhookView(APIView):
    """Receive payment callbacks from Visa/payment provider"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Expected payload:
        {
            "transaction_id": "visa_123456",
            "user_id": 1,
            "plan_type": "premium",
            "amount": 29.99,
            "status": "completed",  # completed, failed, pending
            "payment_method": "visa",
            "raw_data": {}  # optional: store full webhook payload
        }
        """
        data = request.data
        transaction_id = data.get("transaction_id")
        user_id = data.get("user_id")
        plan_type = data.get("plan_type", "free")
        amount = data.get("amount", 0)
        payment_status = data.get("status", "pending")
        payment_method = data.get("payment_method", "visa")
        raw_data = data.get("raw_data", {})

        if not transaction_id or not user_id:
            return Response(
                {"detail": "transaction_id and user_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists
        user = User.objects.filter(id=user_id).first()

        # If user doesn't exist, check for pending registration (organization)
        if not user:
            from tafahom_api.apps.v1.authentication.models import PendingRegistration
            pending = PendingRegistration.objects.filter(
                email__iexact=data.get("email", ""),
                registration_type="organization",
                is_verified=True
            ).first()

            if pending and payment_status == "completed":
                # Create organization user after successful payment
                user = pending.create_organization_user()
                pending.delete()

                # Create payment transaction
                PaymentTransaction.objects.create(
                    transaction_id=transaction_id,
                    user=user,
                    subscription=user.subscription,
                    amount=amount,
                    currency="USD",
                    status=payment_status,
                    provider=payment_method,
                    payment_method=payment_method,
                    webhook_data=raw_data,
                )

                return Response({
                    "message": "Organization account created successfully",
                    "user_id": user.id,
                    "subscription_status": "active",
                    "transaction_id": transaction_id
                })

            return Response(
                {"detail": "User not found and no pending registration"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get or create subscription for existing user
        subscription, _ = Subscription.objects.get_or_create(
            user=user,
            defaults={"plan": SubscriptionPlan.objects.get(plan_type="free")}
        )

        # Create or update payment transaction
        payment, created = PaymentTransaction.objects.update_or_create(
            transaction_id=transaction_id,
            defaults={
                "user": user,
                "subscription": subscription,
                "amount": amount,
                "currency": "USD",
                "status": payment_status,
                "provider": payment_method,
                "payment_method": payment_method,
                "webhook_data": raw_data,
            }
        )

        # Update subscription status based on payment
        with transaction.atomic():
            if payment_status == "completed":
                # Payment successful - activate subscription
                plan = SubscriptionPlan.objects.get(plan_type=plan_type)
                subscription.plan = plan
                subscription.status = "active"
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timezone.timedelta(days=30)
                subscription.save()

                # Update subscription reference in payment
                payment.subscription = subscription
                payment.save()

            elif payment_status == "failed":
                subscription.status = "cancelled"
                subscription.save()

            elif payment_status == "refunded":
                subscription.status = "cancelled"
                subscription.save()

        return Response({
            "message": f"Payment {payment_status}",
            "subscription_status": subscription.status,
            "transaction_id": transaction_id
        })


class PaymentVerifyView(APIView):
    """Check payment status (for frontend polling if needed)"""
    permission_classes = [AllowAny]

    def get(self, request, transaction_id):
        try:
            payment = PaymentTransaction.objects.get(transaction_id=transaction_id)
            return Response({
                "status": payment.status,
                "amount": payment.amount,
                "provider": payment.provider,
                "created_at": payment.created_at,
            })
        except PaymentTransaction.DoesNotExist:
            return Response(
                {"detail": "Transaction not found"},
                status=status.HTTP_404_NOT_FOUND
            )
