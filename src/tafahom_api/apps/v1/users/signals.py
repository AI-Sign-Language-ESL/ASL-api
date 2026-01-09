from django.db.utils import OperationalError, ProgrammingError
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from tafahom_api.apps.v1.billing.models import SubscriptionPlan, Subscription


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
        if free_plan:
            Subscription.objects.get_or_create(
                user=instance,
                defaults={"plan": free_plan},
            )
    except (OperationalError, ProgrammingError):
        # DB not ready (migrate / createsuperuser / tests)
        pass
