from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Organization

from tafahom_api.apps.v1.users.models import User

# =========================
# BASIC USER REGISTRATION
# =========================


class BasicUserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    # Accept ALL common frontend styles
    confirmPassword = serializers.CharField(write_only=True, required=False)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        confirm = (
            data.get("confirmPassword")
            or data.get("password_confirmation")
            or data.get("password_confirm")
        )

        if not confirm:
            raise serializers.ValidationError(
                {"confirmPassword": "Password confirmation is required."}
            )

        if data["password"] != confirm:
            raise serializers.ValidationError(
                {"confirmPassword": "Passwords do not match."}
            )

        validate_password(data["password"])

        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError({"username": "Username already exists."})

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        return data

    def create(self, validated_data):
        for key in ["confirmPassword", "password_confirmation", "password_confirm"]:
            validated_data.pop(key, None)

        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role="basic_user",
        )


# =========================
# ORGANIZATION REGISTRATION
# =========================


class OrganizationRegistrationSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    activity_type = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    confirmPassword = serializers.CharField(write_only=True, required=False)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)

    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    job_title = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        confirm = (
            data.get("confirmPassword")
            or data.get("password_confirmation")
            or data.get("password_confirm")
        )

        if not confirm:
            raise serializers.ValidationError(
                {"confirmPassword": "Password confirmation is required."}
            )

        if data["password"] != confirm:
            raise serializers.ValidationError(
                {"confirmPassword": "Passwords do not match."}
            )

        validate_password(data["password"])

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

        return data

    def create(self, validated_data):
        for key in ["confirmPassword", "password_confirmation", "password_confirm"]:
            validated_data.pop(key, None)

        base_username = validated_data["organization_name"].replace(" ", "_").lower()
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


# =========================
# USER RESPONSE
# =========================


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")


# =========================
# PROFILE / EMAIL
# =========================


class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]
