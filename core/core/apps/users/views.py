from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    LoginSerializer,
    BasicUserRegistrationSerializer,
    OrganizationRegistrationSerializer,
    LoginResponseSerializer,
    RegistrationResponseSerializer,
    UserResponseSerializer,
)


class LoginView(ListAPIView):
    """
    POST /auth/login/

    Request Body:
    {
        "username": "string",
        "password": "string"
    }

    Response Body:
    {
        "access": "string",
        "refresh": "string",
        "user": {
            "id": 0,
            "username": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string",
            "role": "string"
        }
    }
    """

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]

            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    # Generate tokens
                    refresh = RefreshToken.for_user(user)

                    # Prepare response
                    response_data = {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "user": UserResponseSerializer(user).data,
                    }

                    response_serializer = LoginResponseSerializer(response_data)
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "Invalid credentials"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BasicUserRegistrationView(ListAPIView):
    """
    POST /auth/register/basic/

    Request Body:
    {
        "username": "string",
        "first_name": "string",
        "last_name": "string",
        "email": "string",
        "password": "string",
        "password_confirmation": "string"
    }

    Response Body:
    {
        "message": "string",
        "user": {
            "id": 0,
            "username": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string",
            "role": "string"
        },
        "tokens": {
            "access": "string",
            "refresh": "string"
        }
    }
    """

    serializer_class = BasicUserRegistrationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Generate tokens
            refresh = RefreshToken.for_user(user)

            # Prepare response
            response_data = {
                "message": "Basic user registered successfully",
                "user": UserResponseSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }

            response_serializer = RegistrationResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationRegistrationView(ListAPIView):
    """
    POST /auth/register/organization/

    Request Body:
    {
        "organization_name": "string",
        "activity_type": "string",
        "email": "string",
        "password": "string",
        "password_confirmation": "string",
        "first_name": "string",
        "last_name": "string",
        "job_title": "string"
    }

    Response Body:
    {
        "message": "string",
        "user": {
            "id": 0,
            "username": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string",
            "role": "string"
        },
        "tokens": {
            "access": "string",
            "refresh": "string"
        }
    }
    """

    serializer_class = OrganizationRegistrationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            organization = serializer.save()
            user = organization.user

            # Generate tokens
            refresh = RefreshToken.for_user(user)

            # Prepare response
            response_data = {
                "message": "Organization registered successfully",
                "user": UserResponseSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }

            response_serializer = RegistrationResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
