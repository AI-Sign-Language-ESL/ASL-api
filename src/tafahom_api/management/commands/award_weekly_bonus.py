import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from tafahom_api.apps.v1.billing.models import Subscription, TokenTransaction
from tafahom_api.apps.v1.dataset.models import DatasetContribution

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Award weekly bonus tokens to users with approved dataset contributions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without actually awarding tokens",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        one_week_ago = timezone.now() - timedelta(days=7)

        users_with_approved = (
            DatasetContribution.objects.filter(
                status="approved",
                reviewed_at__gte=one_week_ago,
            )
            .values("contributor")
            .annotate(approved_count=Count("id"))
        )

        bonus_per_user = 50

        for user_data in users_with_approved:
            user_id = user_data["contributor"]
            approved_count = user_data["approved_count"]

            if approved_count == 0:
                continue

            try:
                subscription = Subscription.objects.get(user_id=user_id)
            except Subscription.DoesNotExist:
                logger.warning(f"No subscription found for user {user_id}, skipping")
                continue

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would award {bonus_per_user} tokens to user {user_id}"
                )
                continue

            subscription.bonus_tokens += bonus_per_user
            subscription.save(update_fields=["bonus_tokens"])

            TokenTransaction.objects.create(
                user=subscription.user,
                subscription=subscription,
                amount=bonus_per_user,
                transaction_type="earned",
                reason=f"weekly_dataset_bonus_{int(timezone.now().timestamp())}",
            )

            logger.info(
                f"Awarded {bonus_per_user} weekly bonus tokens to user {user_id}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Weekly bonus completed. Processed {len(users_with_approved)} users."
            )
        )