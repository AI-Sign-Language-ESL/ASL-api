import pytest
from rest_framework_simplejwt.tokens import AccessToken
from src.tafahom_api.apps.v1.users.models import Organization, User



# =====================================================
# USERS
# =====================================================

@pytest.fixture
def basic_user(db) -> User:
    return User.objects.create_user(
        username="basicuser",
        email="basic@example.com",
        password="basicpass",
        first_name="Basic",
        last_name="User",
        role="basic_user",
    )


@pytest.fixture
def organization_user(db) -> User:
    user = User.objects.create_user(
        username="orguser",
        email="org@example.com",
        password="orgpass",
        first_name="Org",
        last_name="User",
        role="organization",
    )

    Organization.objects.create(
        user=user,
        organization_name="Test Org",
        activity_type="Education",
        job_title="Manager",
    )

    return user


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
def jwt_basic_user_token(basic_user) -> str:
    return str(AccessToken.for_user(basic_user))


@pytest.fixture
def jwt_org_user_token(organization_user) -> str:
    return str(AccessToken.for_user(organization_user))


@pytest.fixture
def jwt_admin_token(admin_user) -> str:
    return str(AccessToken.for_user(admin_user))
