import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient
from django.test import override_settings

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
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == existing_user.email

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
    def _fresh_cache(self):
        """Return a unique locmem cache override to avoid throttle sharing."""
        from uuid import uuid4
        return override_settings(
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": f"test-google-{uuid4().hex}",
                }
            },
        )

    def test_google_login_success(self, client: APIClient, existing_user, monkeypatch):
        with self._fresh_cache():
            def fake_google_auth(token):
                return existing_user

            monkeypatch.setattr(
                "tafahom_api.apps.v1.authentication.views.authenticate_with_google",
                fake_google_auth,
            )

            response: Response = client.post(
                "/authentication/login/google/",
                {"id_token": "xxxxxxxxxx-fake-google-id-token-xxxxxxxxxx"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert "access" in response.data
            assert "refresh" in response.data
            assert "user" in response.data
            assert response.data["user"]["email"] == existing_user.email

    def test_google_login_missing_token(self, client: APIClient):
        with self._fresh_cache():
            response: Response = client.post(
                "/authentication/login/google/",
                {},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_google_login_invalid_token_format(self, client: APIClient):
        with self._fresh_cache():
            response: Response = client.post(
                "/authentication/login/google/",
                {"id_token": ""},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_google_login_rejected_by_service(self, client: APIClient, monkeypatch):
        with self._fresh_cache():
            def fake_google_auth_fail(token):
                raise ValueError("Google account email is not verified.")

            monkeypatch.setattr(
                "tafahom_api.apps.v1.authentication.views.authenticate_with_google",
                fake_google_auth_fail,
            )

            response: Response = client.post(
                "/authentication/login/google/",
                {"id_token": "xxxxxxxxxx-fake-google-token-xxxxxxxxxx"},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_google_login_existing_user_linking(
        self, client: APIClient, existing_user, monkeypatch
    ):
        with self._fresh_cache():
            def fake_google_auth(token):
                existing_user.google_id = "google-sub-123"
                return existing_user

            monkeypatch.setattr(
                "tafahom_api.apps.v1.authentication.views.authenticate_with_google",
                fake_google_auth,
            )

            response: Response = client.post(
                "/authentication/login/google/",
                {"id_token": "xxxxxxxxxx-fake-google-token-xxxxxxxxxx"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["user"]["email"] == existing_user.email


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
            {"refresh": str(refresh)},  # ✅ FIX HERE
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


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
# 🚪 LOGOUT
# ======================================================


@pytest.mark.django_db
class TestLogoutAPI:
    def _fresh_cache(self):
        """Return a unique locmem cache override to avoid throttle sharing."""
        from uuid import uuid4
        return override_settings(
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": f"test-logout-{uuid4().hex}",
                }
            },
        )

    def test_logout_success(self, client: APIClient, existing_user):
        with self._fresh_cache():
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(existing_user)
            access = str(refresh.access_token)

            response: Response = client.post(
                "/authentication/logout/",
                {"refresh": str(refresh)},
                HTTP_AUTHORIZATION=f"Bearer {access}",
            )

            assert response.status_code == status.HTTP_200_OK

    def test_logout_requires_auth(self, client: APIClient):
        with self._fresh_cache():
            response: Response = client.post(
                "/authentication/logout/",
                {"refresh": "some-token"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_invalid_token(self, client: APIClient, existing_user):
        with self._fresh_cache():
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(existing_user)
            access = str(refresh.access_token)

            response: Response = client.post(
                "/authentication/logout/",
                {"refresh": "invalid-token"},
                HTTP_AUTHORIZATION=f"Bearer {access}",
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
