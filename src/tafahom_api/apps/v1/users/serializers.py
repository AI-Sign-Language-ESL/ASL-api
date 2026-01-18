from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from tafahom_api.apps.v1.users.models import User
from .models import Organization


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

    confirmPassword = serializers.CharField(write_only=True, required=False)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username already exists."})

        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        return attrs

    def create(self, validated_data):
        self._pop_confirmation_fields(validated_data)

        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role="basic_user",
        )


# ======================================================
# 🏢 ORGANIZATION REGISTRATION
# ======================================================


class OrganizationRegistrationSerializer(
    PasswordConfirmationMixin, serializers.Serializer
):
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

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        self._pop_confirmation_fields(validated_data)

        base_username = (
            validated_data["organization_name"].strip().lower().replace(" ", "_")
        )

        if User.objects.filter(username=base_username).exists():
            base_username = f"{base_username}_{validated_data['email'].split('@')[0]}"

        user = User.objects.create_user(
            username=base_username,
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role="organization",
        )

        Organization.objects.create(
            user=user,
            organization_name=validated_data["organization_name"],
            activity_type=validated_data["activity_type"],
            job_title=validated_data.get("job_title", ""),
        )

        return user


# ======================================================
# 👤 USER RESPONSE (FLUTTER SAFE)
# ======================================================


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
        )


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
