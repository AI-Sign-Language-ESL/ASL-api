from django.db.utils import OperationalError, ProgrammingError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

from .models import User


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        SubscriptionPlan = apps.get_model("billing", "SubscriptionPlan")
        Subscription = apps.get_model("billing", "Subscription")

        free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
        if free_plan:
            Subscription.objects.get_or_create(
                user=instance,
                defaults={"plan": free_plan},
            )
    except (OperationalError, ProgrammingError, LookupError):
        # DB not ready / migrations / app registry not ready
        pass
