"""
Security Test Suite for Tafahom API
=====================================
Tests every vulnerability identified in the security audit:

1. Authentication rate limiting (brute-force prevention)
2. Token race condition / double-spend prevention
3. File upload security (magic-byte validation, path traversal)
4. JWT token blacklisting after rotation
5. CORS configuration
6. User enumeration resistance

Run with:
    pytest tests/test_security.py -v
"""

import io
import json
import struct
import threading
import time
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def verified_user(db):
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="SecureP@ssword123!",
        is_verified=True,
        role="basic_user",
    )
    return user


@pytest.fixture
def auth_client(db, verified_user):
    client = APIClient()
    refresh = RefreshToken.for_user(verified_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, verified_user, refresh


@pytest.fixture
def subscription_with_1_token(db, verified_user):
    """Create a subscription with exactly 1 token — for race condition tests."""
    from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan
    plan, _ = SubscriptionPlan.objects.get_or_create(
        plan_type="free",
        defaults={"name": "Free", "weekly_tokens_limit": 1, "price": 0},
    )
    sub = Subscription.objects.create(
        user=verified_user,
        plan=plan,
        status="active",
        tokens_used=0,
        bonus_tokens=0,
    )
    return sub


# ===========================================================================
# 1. AUTHENTICATION RATE LIMITING
# ===========================================================================

@pytest.mark.django_db
class TestLoginRateThrottle:
    """
    Verify that LoginRateThrottle blocks excessive login attempts.
    The throttle is set to 5/minute; the 6th attempt must return HTTP 429.
    """

    LOGIN_URL = "/api/v1/authentication/login/"

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
        RATELIMIT_ENABLED=True,
    )
    def test_login_throttled_after_5_attempts(self, api_client, db):
        payload = {"email": "nonexistent@example.com", "password": "wrong"}

        responses = []
        for _ in range(6):
            r = api_client.post(self.LOGIN_URL, payload, format="json")
            responses.append(r.status_code)

        # First 5 can be 401 (wrong creds) or 403 — NOT 429
        assert all(s != status.HTTP_429_TOO_MANY_REQUESTS for s in responses[:5]), (
            "First 5 requests should not be throttled"
        )
        # 6th must be throttled
        assert responses[5] == status.HTTP_429_TOO_MANY_REQUESTS, (
            "6th login attempt within 1 minute must be rejected with 429"
        )

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
        RATELIMIT_ENABLED=True,
    )
    def test_password_reset_throttled_after_3_attempts(self, api_client, db):
        url = "/api/v1/authentication/password-reset/"
        payload = {"email": "anyone@example.com"}

        responses = [api_client.post(url, payload, format="json").status_code for _ in range(4)]

        assert all(s != status.HTTP_429_TOO_MANY_REQUESTS for s in responses[:3]), (
            "First 3 password reset requests should not be throttled"
        )
        assert responses[3] == status.HTTP_429_TOO_MANY_REQUESTS, (
            "4th password reset request within 1 minute must be rejected with 429"
        )

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
        RATELIMIT_ENABLED=True,
    )
    def test_verify_email_throttled_after_10_attempts(self, api_client, db, verified_user):
        url = "/api/v1/authentication/verify-email/"
        payload = {"email": verified_user.email, "code": "000000"}

        responses = [api_client.post(url, payload, format="json").status_code for _ in range(11)]

        assert all(s != status.HTTP_429_TOO_MANY_REQUESTS for s in responses[:10]), (
            "First 10 verify-email attempts should not be throttled"
        )
        assert responses[10] == status.HTTP_429_TOO_MANY_REQUESTS, (
            "11th OTP attempt within 1 minute must be rejected with 429"
        )


# ===========================================================================
# 2. TOKEN RACE CONDITION (Double-Spend Prevention)
# ===========================================================================

@pytest.mark.django_db(transaction=True)
class TestTokenRaceCondition:
    """
    Simulate N concurrent requests that each try to consume 1 token
    from an account with exactly 1 token. Only 1 should succeed.
    """

    CONCURRENCY = 10

    def _consume_once(self, subscription_pk, results, index):
        """Worker: re-fetch the subscription and attempt to consume 1 token."""
        from tafahom_api.apps.v1.billing.models import Subscription
        try:
            sub = Subscription.objects.get(pk=subscription_pk)
            sub.consume(1)
            results[index] = "success"
        except ValueError:
            results[index] = "insufficient"
        except Exception as e:
            results[index] = f"error: {e}"

    def test_only_one_concurrent_consume_succeeds(self, db, subscription_with_1_token):
        sub = subscription_with_1_token
        assert sub.remaining_tokens() == 1, "Precondition: subscription must have exactly 1 token"

        results = [None] * self.CONCURRENCY
        threads = [
            threading.Thread(target=self._consume_once, args=(sub.pk, results, i))
            for i in range(self.CONCURRENCY)
        ]

        # Launch all threads simultaneously
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = results.count("success")
        failures = results.count("insufficient")

        assert successes == 1, (
            f"Exactly 1 concurrent consume should succeed, got {successes}. "
            f"Results: {results}"
        )
        assert failures == self.CONCURRENCY - 1, (
            f"All other {self.CONCURRENCY - 1} concurrent requests should fail with "
            f"'insufficient tokens', got {failures}."
        )

        # Verify the DB reflects only 1 consumed token
        sub.refresh_from_db()
        assert sub.remaining_tokens() == 0, (
            "After the single successful consume the subscription balance should be 0"
        )

    def test_consume_raises_on_empty_balance(self, db, subscription_with_1_token):
        sub = subscription_with_1_token
        sub.consume(1)           # drain the only token
        with pytest.raises(ValueError, match="Not enough tokens"):
            sub.consume(1)       # must raise, not silently over-draft


# ===========================================================================
# 3. FILE UPLOAD SECURITY
# ===========================================================================

def _make_mp4_bytes(size=100) -> bytes:
    """Construct minimal valid MP4 magic bytes followed by padding."""
    # ftyp box: size(4) + 'ftyp'(4) + brand(4) = 12 bytes minimum
    box_size = struct.pack(">I", 20)          # big-endian uint32
    ftyp = b"ftyp" + b"mp42" + b"\x00" * 8
    return box_size + ftyp + b"\x00" * max(0, size - 20)


def _make_webm_bytes(size=100) -> bytes:
    """Construct minimal valid WebM magic bytes."""
    ebml_header = b"\x1a\x45\xdf\xa3"
    return ebml_header + b"\x00" * max(0, size - 4)


def _make_avi_bytes(size=100) -> bytes:
    """Construct minimal valid AVI magic bytes."""
    return b"RIFF" + struct.pack("<I", size - 8) + b"AVI " + b"\x00" * max(0, size - 12)


@pytest.mark.django_db
class TestFileUploadSecurity:

    UPLOAD_URL = "/api/v1/dataset/contribute/"

    def _upload(self, auth_client, filename, content, content_type="video/mp4"):
        video_file = io.BytesIO(content)
        video_file.name = filename
        return auth_client.post(
            self.UPLOAD_URL,
            {"word": "hello", "video": video_file},
            format="multipart",
        )

    # ── 3a. Valid files are accepted ─────────────────────────────────────────

    def test_valid_mp4_accepted(self, auth_client, db):
        client, _, _ = auth_client
        r = self._upload(client, "sign.mp4", _make_mp4_bytes(2048))
        assert r.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK), (
            f"Valid MP4 should be accepted; got {r.status_code}: {r.data}"
        )

    def test_valid_webm_accepted(self, auth_client, db):
        client, _, _ = auth_client
        r = self._upload(client, "sign.webm", _make_webm_bytes(2048))
        assert r.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_valid_avi_accepted(self, auth_client, db):
        client, _, _ = auth_client
        r = self._upload(client, "sign.avi", _make_avi_bytes(2048))
        assert r.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    # ── 3b. Malicious content is rejected ────────────────────────────────────

    def test_php_shell_disguised_as_mp4_rejected(self, auth_client, db):
        """An attacker renames a PHP shell to .mp4 — magic bytes reveal the truth."""
        client, _, _ = auth_client
        php_content = b"<?php system($_GET['cmd']); ?>"
        r = self._upload(client, "shell.mp4", php_content)
        assert r.status_code == status.HTTP_400_BAD_REQUEST, (
            "PHP shell disguised as .mp4 must be rejected via magic-byte check"
        )

    def test_html_disguised_as_mp4_rejected(self, auth_client, db):
        client, _, _ = auth_client
        html_content = b"<html><script>alert(1)</script></html>"
        r = self._upload(client, "xss.mp4", html_content)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_executable_rejected(self, auth_client, db):
        client, _, _ = auth_client
        elf_header = b"\x7fELF" + b"\x00" * 96    # Linux ELF magic bytes
        r = self._upload(client, "malware.mp4", elf_header)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_disallowed_extension_rejected(self, auth_client, db):
        """Even with valid video magic bytes, a .exe extension is blocked."""
        client, _, _ = auth_client
        r = self._upload(client, "video.exe", _make_mp4_bytes(2048))
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_file_exceeding_size_limit_rejected(self, auth_client, db):
        """Files over 50 MB must be rejected before any processing."""
        client, _, _ = auth_client
        large_content = _make_mp4_bytes(2048) + b"\x00" * (50 * 1024 * 1024 + 1)
        r = self._upload(client, "toobig.mp4", large_content)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    # ── 3c. Path traversal prevention ────────────────────────────────────────

    def test_path_traversal_filename_does_not_escape_media_root(self, db):
        """
        Verify _assert_within_media_root() raises ValueError for traversal paths.
        We test the guard function directly since Django's storage backend already
        strips leading slashes before writing — but our guard is a defence-in-depth layer.
        """
        from tafahom_api.apps.v1.dataset.views import _assert_within_media_root
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                # A path inside MEDIA_ROOT should pass
                safe = os.path.join(tmpdir, "dataset", "videos", "ok.mp4")
                _assert_within_media_root(safe)   # must not raise

                # A path that escapes MEDIA_ROOT must raise
                traversal = os.path.join(tmpdir, "..", "etc", "passwd")
                with pytest.raises(ValueError, match="escapes MEDIA_ROOT"):
                    _assert_within_media_root(traversal)

    def test_convert_to_mp4_blocks_path_traversal(self, db):
        """
        convert_to_mp4() must return None (and log an error) when the
        source path escapes MEDIA_ROOT — never invoke FFmpeg in that case.
        """
        import tempfile
        from tafahom_api.apps.v1.dataset.views import convert_to_mp4

        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                evil_path = os.path.join(tmpdir, "..", "etc", "passwd.avi")
                result = convert_to_mp4(evil_path)
                assert result is None, (
                    "convert_to_mp4() must return None for paths that escape MEDIA_ROOT"
                )


# ===========================================================================
# 4. JWT TOKEN BLACKLISTING AFTER ROTATION
# ===========================================================================

@pytest.mark.django_db
class TestJWTBlacklisting:
    """
    After a refresh token is rotated (used to get a new pair), the old
    refresh token must be blacklisted and rejected on a subsequent use.
    """

    REFRESH_URL = "/api/v1/auth/refresh/"   # adjust if your route differs

    def test_old_refresh_token_blacklisted_after_rotation(self, verified_user, api_client, db):
        refresh = RefreshToken.for_user(verified_user)
        old_refresh_str = str(refresh)

        # First rotation: old → new
        r1 = api_client.post(self.REFRESH_URL, {"refresh": old_refresh_str}, format="json")
        if r1.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Refresh URL not mounted at expected path — adjust REFRESH_URL")

        assert r1.status_code == status.HTTP_200_OK, f"First refresh failed: {r1.data}"

        # Reusing the old refresh token must now fail
        r2 = api_client.post(self.REFRESH_URL, {"refresh": old_refresh_str}, format="json")
        assert r2.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST
        ), (
            f"Re-using a rotated refresh token must be rejected; got {r2.status_code}. "
            "Ensure BLACKLIST_AFTER_ROTATION=True and token_blacklist is in INSTALLED_APPS."
        )


# ===========================================================================
# 5. CORS CONFIGURATION
# ===========================================================================

@pytest.mark.django_db
class TestCORSConfiguration:
    """
    Verify CORS_ALLOW_ALL_ORIGINS is False so arbitrary origins cannot
    access credentialed endpoints.
    """

    def test_cors_allow_all_origins_is_false(self):
        from django.conf import settings
        allow_all = getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
        assert allow_all is False, (
            "CORS_ALLOW_ALL_ORIGINS must be False. "
            "An open wildcard CORS policy allows any website to make "
            "credentialed requests to the API on behalf of logged-in users."
        )

    def test_cors_allowed_origins_is_defined(self):
        from django.conf import settings
        origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        # In production there must be at least one explicit origin
        # (in dev this may be empty — we skip rather than fail)
        if getattr(settings, "ENVIRONMENT", "DEV") == "PROD":
            assert len(origins) > 0, (
                "CORS_ALLOWED_ORIGINS must list at least one origin in PROD"
            )


# ===========================================================================
# 6. USER ENUMERATION RESISTANCE
# ===========================================================================

@pytest.mark.django_db
class TestUserEnumeration:
    """
    Login and password-reset endpoints must return identical responses
    for existing and non-existing accounts to prevent email enumeration.
    """

    def test_login_same_message_for_existing_and_missing_email(
        self, api_client, db, verified_user
    ):
        url = "/api/v1/authentication/login/"
        wrong_password = "WrongPassword999!"

        # Existing account, wrong password
        r_existing = api_client.post(
            url,
            {"email": verified_user.email, "password": wrong_password},
            format="json",
        )
        # Non-existing account
        r_missing = api_client.post(
            url,
            {"email": "nobody@nowhere.com", "password": wrong_password},
            format="json",
        )

        assert r_existing.status_code == r_missing.status_code, (
            "Login must return the same HTTP status for existing vs non-existing accounts"
        )
        assert r_existing.data.get("detail") == r_missing.data.get("detail"), (
            "Login must return the same error message for existing vs non-existing accounts "
            "to prevent email enumeration"
        )

    def test_password_reset_same_response_for_existing_and_missing_email(
        self, api_client, db, verified_user
    ):
        url = "/api/v1/authentication/password-reset/"

        r_existing = api_client.post(url, {"email": verified_user.email}, format="json")
        r_missing = api_client.post(url, {"email": "nobody@nowhere.com"}, format="json")

        assert r_existing.status_code == r_missing.status_code == status.HTTP_200_OK
        assert r_existing.data.get("detail") == r_missing.data.get("detail"), (
            "Password reset must return the same message whether the email exists or not"
        )


# ===========================================================================
# 7. IDOR — Admin endpoints must enforce object-level authorisation
# ===========================================================================

@pytest.mark.django_db
class TestIDOR:
    """
    Verify that a regular authenticated user cannot access admin endpoints
    by providing arbitrary user IDs (IDOR via role escalation).
    """

    def test_regular_user_cannot_access_admin_user_list(self, auth_client, db):
        client, _, _ = auth_client
        r = client.get("/api/v1/users/admin/users/")
        assert r.status_code in (
            status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED
        ), (
            f"Regular user must not access admin user list; got {r.status_code}"
        )

    def test_regular_user_cannot_change_another_users_plan(
        self, auth_client, db, verified_user
    ):
        client, _, _ = auth_client
        # Try to escalate another user to 'premium' plan
        r = client.post(
            f"/api/v1/users/admin/users/{verified_user.pk}/change-plan/",
            {"plan_type": "premium"},
            format="json",
        )
        assert r.status_code in (
            status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED
        ), (
            f"Regular user must not change plan via admin endpoint; got {r.status_code}"
        )

    def test_regular_user_cannot_change_role(self, auth_client, db, verified_user):
        client, _, _ = auth_client
        r = client.post(
            f"/api/v1/users/admin/users/{verified_user.pk}/change-role/",
            {"role": "admin"},
            format="json",
        )
        assert r.status_code in (
            status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED
        ), (
            f"Regular user must not escalate roles via admin endpoint; got {r.status_code}"
        )


# ===========================================================================
# 8. UNAUTHENTICATED ACCESS PREVENTION
# ===========================================================================

@pytest.mark.django_db
class TestUnauthenticatedAccess:
    """
    Endpoints that require authentication must reject unauthenticated requests.
    """

    PROTECTED_ENDPOINTS = [
        ("GET",  "/api/v1/users/me/"),
        ("GET",  "/api/v1/billing/subscription/"),
        ("GET",  "/api/v1/billing/tokens/"),
        ("POST", "/api/v1/dataset/contribute/"),
        ("GET",  "/api/v1/authentication/login-attempts/"),
    ]

    def test_all_protected_endpoints_reject_anonymous(self, api_client, db):
        client = APIClient()   # no credentials
        failures = []

        for method, url in self.PROTECTED_ENDPOINTS:
            response = getattr(client, method.lower())(url)
            if response.status_code not in (
                status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
            ):
                failures.append(
                    f"{method} {url} returned {response.status_code} "
                    f"(expected 401 or 403)"
                )

        assert not failures, (
            "The following endpoints are accessible without authentication:\n"
            + "\n".join(failures)
        )


# ===========================================================================
# 9. MISSING IMPORT for os (used in path-traversal tests above)
# ===========================================================================
import os   # noqa: E402  — intentionally placed at module bottom to be explicit
