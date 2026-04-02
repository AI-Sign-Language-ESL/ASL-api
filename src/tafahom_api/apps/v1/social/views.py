from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from tafahom_api.common.decorators import require_token_and_plan
from tafahom_api.apps.v1.billing.models import TokenTransaction

class YouTubeIntegrationView(APIView):
    """
    Placeholder for YouTube integration. Available for GO and Premium plans.
    """
    @require_token_and_plan(token_cost=30, min_plan="go", feature_name="YouTube Integration")
    def post(self, request):
        subscription = request.subscription
        
        with transaction.atomic():
            subscription.consume(30)
            TokenTransaction.objects.create(
                user=request.user,
                subscription=subscription,
                amount=-30,
                transaction_type="used",
                reason="YouTube video translation"
            )
            
        return Response({
            "message": "YouTube video analysis started.",
            "remaining_tokens": subscription.remaining_tokens()
        }, status=status.HTTP_200_OK)
