import pytest
from rest_framework_simplejwt.tokens import AccessToken
from src.tafahom_api.apps.v1.users.models import User


# =====================================================
# USERS
# =====================================================

@pytest.fixture
def existing_user(db) -> User:
    return User.objects.create_user(
        username="existinguser",
        email="existinguser@example.com",
        password="testpass",
        first_name="Existing",
        last_name="User",
        role="basic_user",
    )


@pytest.fixture
def organization_user(db) -> User:
    return User.objects.create_user(
        username="orguser",
        email="org@example.com",
        password="orgpass",
        first_name="Org",
        last_name="User",
        role="organization",
    )


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )


# =====================================================
# JWT TOKENS (NU-QURAN STYLE)
# =====================================================

@pytest.fixture
def jwt_user_token(existing_user) -> str:
    return str(AccessToken.for_user(existing_user))


@pytest.fixture
def jwt_org_token(organization_user) -> str:
    return str(AccessToken.for_user(organization_user))


@pytest.fixture
def jwt_admin_token(admin_user) -> str:
    return str(AccessToken.for_user(admin_user))
