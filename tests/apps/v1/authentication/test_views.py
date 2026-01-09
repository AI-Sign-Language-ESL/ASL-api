import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from tafahom_api.apps.v1.authentication import models


# ======================================================
# 🔐 LOGIN
# ======================================================


@pytest.mark.django_db
class TestLoginAPI:
    def test_login_success(self, client: APIClient, existing_user, jwt_user_token):
        response: Response = client.post(
            "/authentication/login/",
            {
                "email": existing_user.email,
                "password": "testpass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

    def test_login_invalid_password(self, client: APIClient, existing_user):
        response: Response = client.post(
            "/authentication/login/",
            {
                "email": existing_user.email,
                "password": "wrong-password",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client: APIClient):
        response: Response = client.post(
            "/authentication/login/",
            {
                "email": "noone@example.com",
                "password": "password",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ======================================================
# 🔐 LOGIN WITH 2FA
# ======================================================


@pytest.mark.django_db
class TestLogin2FAAPI:
    def test_login_2fa_invalid_token(self, client: APIClient, existing_user):
        models.TwoFactorAuth.objects.create(
            user=existing_user,
            secret_key="INVALIDSECRET",
            is_enabled=True,
        )

        response: Response = client.post(
            "/authentication/login/2fa/",
            {
                "user_id": existing_user.id,
                "token": "000000",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_2fa_invalid_user(self, client: APIClient):
        response: Response = client.post(
            "/authentication/login/2fa/",
            {
                "user_id": 999999,
                "token": "000000",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ======================================================
# 🌐 GOOGLE LOGIN
# ======================================================


@pytest.mark.django_db
class TestGoogleLoginAPI:
    def test_google_login_success(self, client: APIClient, existing_user, monkeypatch):
        def fake_google_auth(token):
            return existing_user

        monkeypatch.setattr(
            "tafahom_api.apps.v1.authentication.views.authenticate_with_google",
            fake_google_auth,
        )

        response: Response = client.post(
            "/authentication/login/google/",
            {"token": "fake-google-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data


# ======================================================
# 🔄 REFRESH TOKEN
# ======================================================


@pytest.mark.django_db
class TestRefreshTokenAPI:
    def test_refresh_token_success(self, client: APIClient, existing_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(existing_user)

        response: Response = client.post(
            "/authentication/token/refresh/",
            {"refresh_token": str(refresh)},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data


# ======================================================
# 🛡️ TWO FACTOR AUTH
# ======================================================


@pytest.mark.django_db
class TestTwoFactorAPI:
    def test_2fa_setup_requires_auth(self, client: APIClient):
        response: Response = client.post("/authentication/2fa/setup/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_2fa_setup_success(self, client: APIClient, existing_user, jwt_user_token):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.post("/authentication/2fa/setup/")

        assert response.status_code == status.HTTP_200_OK
        assert "qr_code" in response.data
        assert "manual_entry_key" in response.data


# ======================================================
# 🔑 PASSWORD MANAGEMENT
# ======================================================


@pytest.mark.django_db
class TestPasswordAPI:
    def test_change_password_success(
        self, client: APIClient, existing_user, jwt_user_token
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.post(
            "/authentication/password/change/",
            {
                "old_password": "testpass",
                "new_password": "NewStrongPass123!",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old_password(
        self, client: APIClient, existing_user, jwt_user_token
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.post(
            "/authentication/password/change/",
            {
                "old_password": "wrong",
                "new_password": "NewStrongPass123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ======================================================
# 🚨 LOGIN ATTEMPTS
# ======================================================


@pytest.mark.django_db
class TestLoginAttemptsAPI:
    def test_user_can_view_own_attempts(
        self, client: APIClient, existing_user, jwt_user_token
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.get("/authentication/login/attempts/")

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_view_all_attempts(
        self, client: APIClient, admin_user, jwt_admin_token
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}")

        response: Response = client.get("/authentication/login/attempts/all/")

        assert response.status_code == status.HTTP_200_OK

    def test_user_cannot_view_all_attempts(self, client: APIClient, jwt_user_token):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.get("/authentication/login/attempts/all/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
