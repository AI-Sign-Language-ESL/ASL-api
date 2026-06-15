import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tafahom_api.settings.dev')
os.environ.setdefault('DJANGO_ENV', 'development')
django.setup()

from tafahom_api.apps.v1.users.models import User
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan

try:
    user = User.objects.get(email='omzsherifpc00@gmail.com')
    
    plan, _ = SubscriptionPlan.objects.get_or_create(
        plan_type='go', 
        defaults={'name': 'GO Plan', 'weekly_tokens_limit': 500, 'price': 0}
    )
    
    sub, _ = Subscription.objects.get_or_create(user=user, defaults={'plan': plan})
    sub.plan = plan
    sub.status = 'active'
    sub.bonus_tokens = 10000
    sub.save()
    
    print("====================================================================")
    print("SUCCESS: Upgraded omzsherifpc00@gmail.com to GO plan with 10,000 bonus tokens!")
    print("====================================================================")
except User.DoesNotExist:
    print("ERROR: User omzsherifpc00@gmail.com not found. Please make sure the user is registered.")
except Exception as e:
    print(f"ERROR: {str(e)}")
