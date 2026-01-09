import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from tafahom_api.apps.v1.dataset.models import DatasetContribution
from tafahom_api.apps.v1.users.models import User


@pytest.mark.django_db
class TestDatasetContributionCreateAPI:
    def test_create_contribution_success(
        self,
        client: APIClient,
        existing_user: User,
        jwt_user_token: str,
        valid_video_file,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        payload = {
            "word": "hello",
            "video": valid_video_file,
        }

        response: Response = client.post(
            "/dataset/contributions/",
            payload,
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert DatasetContribution.objects.count() == 1
        assert DatasetContribution.objects.first().status == "pending"

    def test_create_requires_auth(self, client: APIClient, valid_video_file):
        response = client.post(
            "/dataset/contributions/",
            {"word": "hello", "video": valid_video_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_invalid_word(
        self,
        client: APIClient,
        jwt_user_token: str,
        valid_video_file,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response = client.post(
            "/dataset/contributions/",
            {"word": "   ", "video": valid_video_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "word" in response.data


@pytest.mark.django_db
class TestMyDatasetContributionsAPI:
    def test_list_my_contributions(
        self,
        client: APIClient,
        existing_user: User,
        jwt_user_token: str,
        dataset_contribution,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.get("/dataset/contributions/me/")

        assert response.status_code == status.HTTP_200_OK

        # FIX: Handle pagination wrapper
        results = (
            response.data["results"] if "results" in response.data else response.data
        )

        assert len(results) == 1
        assert results[0]["word"] == "hello"


@pytest.mark.django_db
class TestPendingDatasetContributionsAPI:
    def test_admin_can_list_pending(
        self,
        client: APIClient,
        admin_user: User,
        jwt_admin_token: str,
        dataset_contribution,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}")

        response: Response = client.get("/dataset/admin/contributions/pending/")

        assert response.status_code == status.HTTP_200_OK

        # FIX: Handle pagination wrapper
        results = (
            response.data["results"] if "results" in response.data else response.data
        )

        assert len(results) == 1
        assert results[0]["id"] == dataset_contribution.id

    def test_non_admin_forbidden(
        self,
        client: APIClient,
        jwt_user_token: str,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response = client.get("/dataset/admin/contributions/pending/")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestApproveDatasetContributionAPI:
    def test_approve_success(
        self,
        client: APIClient,
        admin_user: User,
        jwt_admin_token: str,
        dataset_contribution,
        free_plan,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}")

        response: Response = client.post(
            f"/dataset/admin/contributions/{dataset_contribution.id}/approve/"
        )

        assert response.status_code == status.HTTP_200_OK

        dataset_contribution.refresh_from_db()
        assert dataset_contribution.status == "approved"
        assert dataset_contribution.reviewer == admin_user


@pytest.mark.django_db
class TestRejectDatasetContributionAPI:
    def test_reject_success(
        self,
        client: APIClient,
        admin_user: User,
        jwt_admin_token: str,
        dataset_contribution,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}")

        response: Response = client.post(
            f"/dataset/admin/contributions/{dataset_contribution.id}/reject/"
        )

        assert response.status_code == status.HTTP_200_OK

        dataset_contribution.refresh_from_db()
        assert dataset_contribution.status == "rejected"

    def test_reject_nonexistent(
        self,
        client: APIClient,
        jwt_admin_token: str,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}")

        response = client.post("/dataset/admin/contributions/999999/reject/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestDatasetPermissions:
    def test_user_cannot_approve(
        self,
        client: APIClient,
        jwt_user_token: str,
        dataset_contribution,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response = client.post(
            f"/dataset/admin/contributions/{dataset_contribution.id}/approve/"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
