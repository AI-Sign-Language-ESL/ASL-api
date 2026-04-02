from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan

def require_token_and_plan(token_cost=0, min_plan="free", feature_name=None):
    """
    Decorator to check if user has enough tokens and the correct plan for a feature.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(view_instance, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            # Get or create subscription (wallet)
            try:
                subscription = user.subscription
            except ObjectDoesNotExist:
                free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
                if not free_plan:
                     return Response({"detail": "System configuration error: No default plan found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                subscription = Subscription.objects.create(
                    user=user,
                    plan=free_plan,
                    status="active"
                )

            # 1. Plan Check
            plan_rank = {"free": 0, "basic": 1, "go": 2, "premium": 3}
            if plan_rank.get(subscription.plan.plan_type, 0) < plan_rank.get(min_plan, 0):
                return Response(
                    {"detail": f"This feature ({feature_name or 'feature'}) is available on {min_plan.upper()} plans and above."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 2. Token Check
            if not subscription.can_consume(token_cost):
                return Response(
                    {"detail": f"Not enough tokens. This feature requires {token_cost} tokens."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Store subscription in request for easy access in the view if needed
            request.subscription = subscription
            
            return view_func(view_instance, request, *args, **kwargs)
        return _wrapped_view
    return decorator
