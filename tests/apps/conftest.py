import pytest
from rest_framework_simplejwt.tokens import AccessToken
from tafahom_api.apps.v1.users.models import User


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.core.management import call_command

        call_command("loaddata", "sign_languages")
        call_command("loaddata", "translations")


@pytest.fixture
def existing_user(db) -> User:
    """
    Base test user
    """
    return User.objects.create_user(
        username="testuser", email="test@test.com", password="password123"
    )


@pytest.fixture
def jwt_user_token(existing_user) -> str:
    token = AccessToken.for_user(existing_user)
    return str(token)


@pytest.fixture
def jwt_admin_token(admin_user) -> str:
    token = AccessToken.for_user(admin_user)
    return str(token)


@pytest.fixture
def jwt_supervisor_token(supervisor_user) -> str:
    token = AccessToken.for_user(supervisor_user)
    return str(token)
