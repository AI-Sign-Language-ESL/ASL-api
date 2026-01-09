import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from tafahom_api.apps.v1.users.models import User, Organization


@pytest.mark.django_db
class TestBasicUserRegistrationAPI:
    def test_register_basic_user_success(self, client: APIClient):
        payload = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "confirmPassword": "StrongPass123!",
        }

        response: Response = client.post("/users/register/basic/", payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["user"]["email"] == "new@example.com"
        assert response.data["user"]["role"] == "basic_user"
        assert "tokens" in response.data
        assert User.objects.filter(email="new@example.com").exists()

    def test_register_basic_user_password_mismatch(self, client: APIClient):
        payload = {
            "username": "baduser",
            "first_name": "Bad",
            "last_name": "User",
            "email": "bad@example.com",
            "password": "pass1",
            "confirmPassword": "pass2",
        }

        response = client.post("/users/register/basic/", payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirmPassword" in response.data


@pytest.mark.django_db
class TestOrganizationRegistrationAPI:
    def test_register_organization_success(self, client: APIClient):
        payload = {
            "organization_name": "Edu Org",
            "activity_type": "Education",
            "email": "org2@example.com",
            "password": "StrongPass123!",
            "confirmPassword": "StrongPass123!",
            "first_name": "Org",
            "last_name": "Owner",
            "job_title": "Director",
        }

        response: Response = client.post("/users/register/organization/", payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["user"]["role"] == "organization"
        assert Organization.objects.filter(organization_name="Edu Org").exists()


@pytest.mark.django_db
class TestMyProfileAPI:
    def test_get_my_profile(
        self,
        client: APIClient,
        basic_user,
        jwt_basic_user_token,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_basic_user_token}")

        response: Response = client.get("/users/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == basic_user.email

    def test_profile_requires_auth(self, client: APIClient):
        response = client.get("/users/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfileUpdateAPI:
    def test_update_profile_success(
        self,
        client: APIClient,
        basic_user,
        jwt_basic_user_token,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_basic_user_token}")

        payload = {"first_name": "Updated", "last_name": "Name"}
        response = client.patch("/users/me/update/", payload)

        assert response.status_code == status.HTTP_200_OK
        basic_user.refresh_from_db()
        assert basic_user.first_name == "Updated"


@pytest.mark.django_db
class TestChangeEmailAPI:
    def test_change_email_success(
        self,
        client: APIClient,
        basic_user,
        jwt_basic_user_token,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_basic_user_token}")

        response = client.patch(
            "/users/me/email/",
            {"email": "updated@example.com"},
        )

        assert response.status_code == status.HTTP_200_OK
        basic_user.refresh_from_db()
        assert basic_user.email == "updated@example.com"


@pytest.mark.django_db
class TestUserPermissions:
    def test_user_cannot_update_other_user(
        self,
        client: APIClient,
        basic_user,
        organization_user,
        jwt_basic_user_token,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_basic_user_token}")

        response = client.patch(
            f"/users/{organization_user.id}/",
            {"first_name": "Hack"},
        )

        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
