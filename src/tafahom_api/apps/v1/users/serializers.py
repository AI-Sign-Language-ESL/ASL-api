from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from tafahom_api.common.emails import send_branded_verification_email
import secrets

from tafahom_api.apps.v1.users.models import User
from .models import Organization
from tafahom_api.apps.v1.authentication.models import EmailVerificationCode, PendingRegistration


# ======================================================
# 🔹 SHARED PASSWORD CONFIRMATION MIXIN
# ======================================================


class PasswordConfirmationMixin:
    """
    Accepts multiple frontend styles:
    - confirmPassword
    - password_confirmation
    - password_confirm
    """

    def validate(self, attrs):
        password = attrs.get("password")

        confirm = (
            attrs.get("confirmPassword")
            or attrs.get("password_confirmation")
            or attrs.get("password_confirm")
        )

        if not confirm:
            raise serializers.ValidationError(
                {"confirmPassword": "Password confirmation is required."}
            )

        if password != confirm:
            raise serializers.ValidationError(
                {"confirmPassword": "Passwords do not match."}
            )

        validate_password(password)
        return attrs

    def _pop_confirmation_fields(self, data):
        for key in ("confirmPassword", "password_confirmation", "password_confirm"):
            data.pop(key, None)


# ======================================================
# 👤 BASIC USER REGISTRATION
# ======================================================


class BasicUserRegistrationSerializer(
    PasswordConfirmationMixin, serializers.Serializer
):
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    org_code = serializers.CharField(max_length=20, required=False, allow_blank=True)

    confirmPassword = serializers.CharField(write_only=True, required=False)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username already exists."})

        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        if PendingRegistration.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username already pending verification."})

        if PendingRegistration.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already pending verification."})

        org_code = attrs.get("org_code", "").strip()
        if org_code:
            org_user = User.objects.filter(
                role="organization",
                organization_profile__org_code=org_code
            ).first()
            if not org_user:
                raise serializers.ValidationError({"org_code": "Invalid organization code."})
            attrs["organization"] = org_user

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        self._pop_confirmation_fields(validated_data)

        code = "".join([secrets.choice("0123456789") for _ in range(6)])

        org = validated_data.get("organization")

        pending = PendingRegistration.objects.create(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=make_password(validated_data["password"]),
            registration_type="basic",
            verification_code=code,
            organization=org,
        )

        send_branded_verification_email(pending.email, code)

        return pending


# ======================================================
# 🏢 ORGANIZATION REGISTRATION
# ======================================================


class OrganizationRegistrationSerializer(
    PasswordConfirmationMixin, serializers.Serializer
):
    username = serializers.CharField(max_length=150)
    organization_name = serializers.CharField(max_length=255)
    activity_type = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    job_title = serializers.CharField(max_length=255, required=False, allow_blank=True)

    confirmPassword = serializers.CharField(write_only=True, required=False)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username already exists."})

        if PendingRegistration.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already pending verification."})

        if PendingRegistration.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username already pending verification."})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        self._pop_confirmation_fields(validated_data)

        code = "".join([secrets.choice("0123456789") for _ in range(6)])

        pending = PendingRegistration.objects.create(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=make_password(validated_data["password"]),
            registration_type="organization",
            organization_name=validated_data["organization_name"],
            activity_type=validated_data["activity_type"],
            job_title=validated_data.get("job_title", ""),
            verification_code=code,
        )

        send_branded_verification_email(pending.email, code)

        return pending


# ======================================================
# 👤 USER RESPONSE (FLUTTER SAFE)
# ======================================================


class UserResponseSerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_verified",
            "is_staff",
            "is_superuser",
            "organization",
            "organization_name",
            "members_count",
        )

    def get_organization_name(self, obj):
        if obj.organization:
            return obj.organization.organization_profile.organization_name if hasattr(obj.organization, 'organization_profile') else None
        return None

    def get_members_count(self, obj):
        return obj.organization_members_count


# ======================================================
# ✏️ PROFILE / EMAIL
# ======================================================


class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = self.context["request"].user
        if User.objects.filter(email__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Email already in use.")
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name")
