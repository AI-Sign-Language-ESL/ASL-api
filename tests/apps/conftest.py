import pytest
from rest_framework_simplejwt.tokens import RefreshToken
from tafahom_api.apps.v1.users.models import User


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.core.management import call_command

        call_command("loaddata", "sign_languages")
        call_command("loaddata", "translations")


@pytest.fixture
def user(db) -> User:
    """
    Base test user
    """
    return User.objects.create_user(
        username="testuser", email="test@test.com", password="password123"
    )


@pytest.fixture
def auth_tokens(user):
    """
    JWT tokens for authenticated requests
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@pytest.fixture
def auth_client(api_client, auth_tokens):
    """
    Authenticated API client
    """
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_tokens['access']}")
    return api_client
