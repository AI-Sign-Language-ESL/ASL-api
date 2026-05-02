from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
import os
import subprocess
import tempfile
from django.core.files import File

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from tafahom_api.apps.v1.billing.services import reward_dataset_contribution

# We import Billing models here to create the wallet if it's missing
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan

from .models import DatasetContribution, InvalidDatasetStatusTransition
from . import serializers


def convert_to_mp4(source_path):
    """
    Convert a video file to MP4 using ffmpeg.
    Returns the path to the converted file, or None if conversion fails.
    """
    ext = os.path.splitext(source_path)[1].lower()
    if ext in ('.mp4', '.webm'):
        return None  # Already browser-compatible, no conversion needed

    output_path = source_path.rsplit('.', 1)[0] + '_converted.mp4'
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-i', source_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-movflags', 'faststart',
                output_path
            ],
            capture_output=True,
            timeout=120
        )
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # ffmpeg not available or timed out
    return None


class DatasetContributionCreateView(generics.CreateAPIView):
    serializer_class = serializers.DatasetContributionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        contribution = serializer.save(contributor=self.request.user)

        # Auto-convert non-browser-compatible formats (mov, avi) to mp4
        if contribution.video:
            source_path = contribution.video.path
            converted_path = convert_to_mp4(source_path)
            if converted_path:
                new_name = os.path.basename(converted_path)
                with open(converted_path, 'rb') as f:
                    contribution.video.save(new_name, File(f), save=True)
                # Clean up both temp files
                try:
                    os.remove(converted_path)
                    os.remove(source_path)
                except OSError:
                    pass


class PendingDatasetContributionsView(generics.ListAPIView):
    serializer_class = serializers.DatasetContributionListSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return DatasetContribution.objects.filter(status="pending").order_by(
            "created_at"
        )


class ApproveDatasetContributionView(generics.GenericAPIView):
    serializer_class = serializers.DatasetContributionActionSerializer
    permission_classes = [permissions.IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        try:
            # OPTIMIZATION: Fetch contribution + user in one query and lock the row
            contribution = (
                DatasetContribution.objects.select_for_update()
                .select_related("contributor")
                .get(pk=pk)
            )

            # 1. Change status to Approved
            contribution.approve(reviewer=request.user)

            # 2. Get or Create the User's "Wallet" (Subscription)
            try:
                subscription = contribution.contributor.subscription
            except ObjectDoesNotExist:
                # 🚨 User has no subscription row (Wallet). We create one now.
                # We assume there is a 'free' plan in your DB.
                default_plan = SubscriptionPlan.objects.filter(plan_type="free").first()

                # If no specific 'free' plan, just grab the first available active plan
                if not default_plan:
                    default_plan = SubscriptionPlan.objects.filter(
                        is_active=True
                    ).first()

                if default_plan:
                    subscription = Subscription.objects.create(
                        user=contribution.contributor,
                        plan=default_plan,
                        status="active",
                        billing_period="monthly",
                        tokens_used=0,
                        bonus_tokens=0,
                    )
                else:
                    # CRITICAL: No plans exist in DB at all. Cannot reward.
                    # We log this internally or just return success without reward.
                    subscription = None

            # 3. Reward the Tokens (if we found/created a wallet)
            if subscription:
                reward_dataset_contribution(
                    subscription=subscription,
                    tokens=10,
                )

        except DatasetContribution.DoesNotExist:
            return Response(
                {"detail": "Contribution not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except InvalidDatasetStatusTransition as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Contribution approved and user rewarded"},
            status=status.HTTP_200_OK,
        )


class RejectDatasetContributionView(generics.GenericAPIView):
    serializer_class = serializers.DatasetContributionActionSerializer
    permission_classes = [permissions.IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        try:
            contribution = DatasetContribution.objects.select_for_update().get(pk=pk)
            contribution.reject(reviewer=request.user)

        except DatasetContribution.DoesNotExist:
            return Response(
                {"detail": "Contribution not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except InvalidDatasetStatusTransition as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Contribution rejected"},
            status=status.HTTP_200_OK,
        )


class MyDatasetContributionsView(generics.ListAPIView):
    serializer_class = serializers.DatasetContributionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DatasetContribution.objects.filter(
            contributor=self.request.user
        ).order_by("-created_at")
