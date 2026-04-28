from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tafahom_api.apps.v1.billing.models import Subscription, TokenTransaction


class Command(BaseCommand):
    help = 'Weekly token reset: resets tokens_used to 0 for users who have used any tokens, restoring them to the full plan limit (50).'

    def handle(self, *args, **options):
        self.stdout.write('Checking weekly token eligibility...')

        try:
            with transaction.atomic():
                active_subs = Subscription.objects.filter(
                    status='active',
                    plan__plan_type='free'
                ).select_related('plan')

                count = 0

                for sub in active_subs:
                    # Only reset if user has actually used some tokens (remaining < plan limit)
                    if sub.tokens_used > 0:
                        tokens_restored = sub.tokens_used  # how many were used

                        # Reset usage to 0 → user is back to full 50 tokens (not 55, not 100)
                        sub.tokens_used = 0
                        sub.last_reset = timezone.now()
                        sub.save(update_fields=['tokens_used', 'last_reset'])

                        # Log the reset as a credit transaction
                        TokenTransaction.objects.create(
                            user=sub.user,
                            subscription=sub,
                            amount=tokens_restored,
                            transaction_type='earned',
                            reason='Weekly token reset'
                        )
                        count += 1

            self.stdout.write(self.style.SUCCESS(f'Reset tokens for {count} eligible users.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Skipping weekly token reset: {e}'))
            # Don't crash the startup if this fails
