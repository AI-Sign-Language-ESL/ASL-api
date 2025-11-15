from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import User
from .serializers import (
    LoginSerializer,
    BasicUserRegistrationSerializer,
    OrganizationRegistrationSerializer,
    LoginResponseSerializer,
    RegistrationResponseSerializer,
    UserResponseSerializer,
)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """
    POST /auth/login/
    """

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)

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


@method_decorator(csrf_exempt, name="dispatch")
class BasicUserRegistrationView(APIView):
    """
    POST /auth/register/basic/
    """

    def post(self, request, *args, **kwargs):
        serializer = BasicUserRegistrationSerializer(data=request.data)

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


@method_decorator(csrf_exempt, name="dispatch")
class OrganizationRegistrationView(APIView):
    """
    POST /auth/register/organization/
    """

    def post(self, request, *args, **kwargs):
        serializer = OrganizationRegistrationSerializer(data=request.data)

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
