from django.core.management.base import BaseCommand
from django.db import transaction
from tafahom_api.apps.v1.billing.models import Subscription, TokenTransaction

class Command(BaseCommand):
    help = 'Award weekly bonus tokens to all active subscribers'

    def handle(self, *args, **options):
        self.stdout.write('Awarding weekly bonus tokens...')
        
        with transaction.atomic():
            active_subs = Subscription.objects.filter(
                status='active',
                plan__plan_type='free'
            ).select_related('plan')
            count = 0
            
            for sub in active_subs:
                # Add 50 bonus tokens as requested
                award_amount = 50
                sub.bonus_tokens += award_amount
                sub.save(update_fields=['bonus_tokens'])
                
                # Record the transaction
                TokenTransaction.objects.create(
                    user=sub.user,
                    subscription=sub,
                    amount=award_amount,
                    transaction_type='earned',
                    reason='Weekly loyalty bonus'
                )
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Successfully awarded tokens to {count} users.'))
