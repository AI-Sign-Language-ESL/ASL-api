from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import logging
import os
import re
import subprocess
from django.core.files import File

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from tafahom_api.apps.v1.billing.services import reward_dataset_contribution

# We import Billing models here to create the wallet if it's missing
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan

from .models import DatasetContribution, InvalidDatasetStatusTransition
from . import serializers

logger = logging.getLogger(__name__)

# Allowlist of safe video extensions for conversion
_CONVERTIBLE_EXTENSIONS = {".avi", ".mov"}

# Only alphanumeric, hyphens, underscores and dots in filenames.
# Anything else is stripped before the path reaches the shell or FFmpeg.
_SAFE_FILENAME_RE = re.compile(r"[^\w.\-]")


def _assert_within_media_root(path: str) -> None:
    """
    Raise ValueError if the resolved path escapes MEDIA_ROOT.
    Defends against path-traversal inputs like  ../../etc/passwd.mp4
    """
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    real_path = os.path.realpath(path)
    if not real_path.startswith(media_root + os.sep) and real_path != media_root:
        raise ValueError(
            f"Security: path '{real_path}' escapes MEDIA_ROOT '{media_root}'"
        )


def convert_to_mp4(source_path: str):
    """
    Convert a video file to MP4 using FFmpeg.

    Security hardening applied here:
    - Path traversal prevention: resolves and asserts the source path stays
      inside MEDIA_ROOT before any OS operation.
    - Filename sanitization: strips non-alphanumeric characters from the
      filename component so malicious names like '-i payload.mp4' cannot
      inject extra FFmpeg flags (shell=False makes this a belt-and-suspenders
      defence; the real protection is that args are passed as a list).
    - The output path is derived from the sanitized source name, not from any
      user-supplied value.

    Returns the path to the converted file, or None if conversion fails.
    """
    # 1. Resolve and validate the source path is inside MEDIA_ROOT
    try:
        _assert_within_media_root(source_path)
    except ValueError:
        logger.error("FFmpeg conversion blocked: path traversal detected for '%s'", source_path)
        return None

    ext = os.path.splitext(source_path)[1].lower()
    if ext not in _CONVERTIBLE_EXTENSIONS:
        # Already browser-compatible (.mp4/.webm) or unsupported — skip
        return None

    # 2. Sanitize the filename to prevent option-injection into FFmpeg.
    #    e.g.  "-i something -vf malicious.avi"  becomes  "-i-something--vf-malicious.avi"
    #    and then FFmpeg receives it as a positional argument, not a flag.
    dir_name = os.path.dirname(source_path)
    raw_name = os.path.splitext(os.path.basename(source_path))[0]
    safe_name = _SAFE_FILENAME_RE.sub("_", raw_name)

    output_path = os.path.join(dir_name, safe_name + "_converted.mp4")

    # Validate the output path as well
    try:
        _assert_within_media_root(output_path)
    except ValueError:
        logger.error("FFmpeg conversion blocked: output path escapes MEDIA_ROOT")
        return None

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", source_path,       # source_path validated above
                "-c:v", "libx264",
                "-c:a", "aac",
                "-movflags", "faststart",
                output_path,             # output_path validated above
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        else:
            logger.warning(
                "FFmpeg conversion failed (exit %s) for '%s'",
                result.returncode, source_path,
            )
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg conversion timed out for '%s'", source_path)
    except FileNotFoundError:
        logger.warning("FFmpeg not found — video conversion skipped")
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
