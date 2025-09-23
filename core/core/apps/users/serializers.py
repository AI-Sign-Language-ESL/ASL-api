from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import User, Organization


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class BasicUserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirmation = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["password_confirmation"]:
            raise serializers.ValidationError("Passwords do not match")

        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError("Username already exists")

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError("Email already exists")

        return data

    def create(self, validated_data):
        validated_data.pop("password_confirmation")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role="basic_user",
        )
        return user


class OrganizationRegistrationSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    activity_type = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirmation = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    job_title = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        if data["password"] != data["password_confirmation"]:
            raise serializers.ValidationError("Passwords do not match")

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError("Email already exists")

        return data

    def create(self, validated_data):
        validated_data.pop("password_confirmation")

        # Create user
        user = User.objects.create_user(
            username=validated_data["organization_name"].replace(" ", "_").lower(),
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role="organization",
        )

        # Create organization
        organization = Organization.objects.create(
            user=user,
            organization_name=validated_data["organization_name"],
            activity_type=validated_data["activity_type"],
            job_title=validated_data.get("job_title", ""),
        )

        return organization


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserResponseSerializer()


class RegistrationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserResponseSerializer()
    tokens = serializers.DictField(child=serializers.CharField())
