from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    BasicUserRegistrationSerializer,
    OrganizationRegistrationSerializer,
    UserResponseSerializer,
    ChangeEmailSerializer,
    ProfileUpdateSerializer,
)

# ======================================================
# 👤 BASIC USER REGISTRATION
# ======================================================


class BasicUserRegistrationView(generics.GenericAPIView):
    serializer_class = BasicUserRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# ======================================================
# 🏢 ORGANIZATION REGISTRATION
# ======================================================


class OrganizationRegistrationView(generics.GenericAPIView):
    serializer_class = OrganizationRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# ======================================================
# 👤 PROFILE (GET)
# ======================================================


class MyProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserResponseSerializer

    def get_object(self):
        return self.request.user


# ======================================================
# ✉️ CHANGE EMAIL
# ======================================================


class ChangeEmailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeEmailSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.email = serializer.validated_data["email"]
        request.user.save(update_fields=["email"])

        return Response(
            {"message": "Email updated successfully"},
            status=status.HTTP_200_OK,
        )


# ======================================================
# ✏️ UPDATE PROFILE
# ======================================================


class ProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user
