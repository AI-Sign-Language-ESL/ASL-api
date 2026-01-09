import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from src.tafahom_api.apps.v1.billing.models import Subscription
from src.tafahom_api.apps.v1.users.models import User

@pytest.mark.django_db
class TestSubscriptionPlansAPI:
    def test_list_active_plans(
        self,
        client: APIClient,
        free_plan,
        paid_plan,
    ):
        response: Response = client.get("/billing/plans/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]["plan_type"] == "free"

    def test_only_active_plans_returned(
        self,
        client: APIClient,
        free_plan,
        paid_plan,
    ):
        paid_plan.is_active = False
        paid_plan.save()

        response: Response = client.get("/billing/plans/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["plan_type"] == "free"

@pytest.mark.django_db
class TestMySubscriptionAPI:
    def test_get_existing_subscription(
        self,
        client: APIClient,
        existing_user: User,
        jwt_user_token: str,
        user_subscription,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        response: Response = client.get("/billing/my-subscription/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "active"
        assert "remaining_credits" in response.data

    def test_free_subscription_created_if_missing(
        self,
        client: APIClient,
        existing_user: User,
        jwt_user_token: str,
        free_plan,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        Subscription.objects.filter(user=existing_user).delete()

        response: Response = client.get("/billing/my-subscription/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["plan"]["plan_type"] == "free"
        assert Subscription.objects.filter(user=existing_user).exists()

    def test_my_subscription_requires_auth(self, client: APIClient):
        response = client.get("/billing/my-subscription/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
class TestSubscribeAPI:
    def test_subscribe_success(
        self,
        client: APIClient,
        existing_user: User,
        jwt_user_token: str,
        paid_plan,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        payload = {
            "plan_id": paid_plan.id,
            "billing_period": "monthly",
        }

        response: Response = client.post(
            "/billing/subscribe/",
            payload,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["plan"]["plan_type"] == "pro"

    def test_subscribe_invalid_plan(
        self,
        client: APIClient,
        jwt_user_token: str,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        response: Response = client.post(
            "/billing/subscribe/",
            {"plan_id": 999999, "billing_period": "monthly"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_subscribe_requires_auth(self, client: APIClient):
        response = client.post(
            "/billing/subscribe/",
            {"plan_id": 1, "billing_period": "monthly"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
class TestCancelSubscriptionAPI:
    def test_cancel_subscription_success(
        self,
        client: APIClient,
        jwt_user_token: str,
        user_subscription,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        response: Response = client.post("/billing/cancel/")

        assert response.status_code == status.HTTP_200_OK
        user_subscription.refresh_from_db()
        assert user_subscription.status == "cancelled"

    def test_cancel_without_subscription(
        self,
        client: APIClient,
        existing_user: User,
        jwt_user_token: str,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        Subscription.objects.filter(user=existing_user).delete()

        response: Response = client.post("/billing/cancel/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No active subscription" in response.data["detail"]
        
@pytest.mark.django_db
class TestBillingPermissions:
    def test_anonymous_user_cannot_subscribe(self, client: APIClient):
        response = client.post("/billing/subscribe/", {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_user_cannot_cancel(self, client: APIClient):
        response = client.post("/billing/cancel/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
