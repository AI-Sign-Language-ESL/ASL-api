import secrets
from typing import Dict

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from tafahom_api.common.emails import send_branded_verification_email, send_password_reset_email

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from rest_framework_simplejwt.tokens import RefreshToken

from tafahom_api.apps.v1.users.models import User
from tafahom_api.apps.v1.users.serializers import UserResponseSerializer

from . import models, serializers
from .services.google_auth import authenticate_with_google


# =====================================================
# 🔐 LOGIN (EMAIL ONLY)
# =====================================================


class LoginView(generics.GenericAPIView):
    serializer_class = serializers.LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"detail": _("Email or password is wrong")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        authenticated_user = authenticate(
            request,
            username=user.username,
            password=password,
        )

        if not authenticated_user:
            return Response(
                {"detail": _("Email or password is wrong")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_verified:
            return Response(
                {
                    "requires_verification": True,
                    "user_id": user.id,
                    "detail": _("Please verify your email before logging in"),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        two_fa = getattr(user, "two_factor_auth", None)
        if two_fa and two_fa.is_enabled:
            return Response(
                {
                    "requires_2fa": True,
                    "user_id": user.id,
                },
                status=status.HTTP_200_OK,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# 🔐 LOGIN WITH 2FA
# =====================================================


class Login2FAView(generics.GenericAPIView):
    serializer_class = serializers.Login2FASerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(id=serializer.validated_data["user_id"])
        two_fa = user.two_factor_auth
        token = serializer.validated_data["token"]

        if not (two_fa.verify_token(token) or two_fa.use_backup_code(token)):
            return Response(
                {"detail": _("Invalid authentication code")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# 🌐 GOOGLE LOGIN (EMAIL-BASED)
# =====================================================


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {"detail": _("Token is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate_with_google(token)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# 🛡️ TWO-FACTOR SETUP
# =====================================================


class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        two_fa, _ = models.TwoFactorAuth.objects.get_or_create(user=request.user)

        if not two_fa.secret_key:
            two_fa.generate_secret_key()

        qr_code = two_fa.generate_qr_code()

        return Response(
            {
                "qr_code": f"data:image/png;base64,{qr_code}",
                "manual_entry_key": two_fa.secret_key,
                "is_enabled": two_fa.is_enabled,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorEnableView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.TwoFactorEnableSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        two_fa = request.user.two_factor_auth

        if not two_fa.verify_token(token):
            return Response(
                {"detail": _("Invalid authentication code")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        two_fa.is_enabled = True
        backup_codes = two_fa.generate_backup_codes()
        two_fa.save()

        return Response(
            {
                "message": _("Two-factor authentication enabled"),
                "backup_codes": backup_codes,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.TwoFactorDisableSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = serializer.validated_data["password"]
        token = serializer.validated_data["token"]

        if authenticate(username=request.user.username, password=password) is None:
            return Response(
                {"detail": _("Invalid password")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        two_fa = request.user.two_factor_auth
        if not two_fa.verify_token(token):
            return Response(
                {"detail": _("Invalid authentication code")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        two_fa.is_enabled = False
        two_fa.secret_key = ""
        two_fa.backup_codes = []
        two_fa.save()

        return Response(
            {"message": _("Two-factor authentication disabled")},
            status=status.HTTP_200_OK,
        )


# =====================================================
# 🚨 LOGIN ATTEMPTS (READ ONLY)
# =====================================================


class MyLoginAttemptsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.LoginAttemptSerializer

    def get_queryset(self):
        return models.LoginAttempt.objects.filter(user=self.request.user).order_by(
            "-attempted_at"
        )


class AllLoginAttemptsView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.LoginAttemptSerializer
    queryset = models.LoginAttempt.objects.all().order_by("-attempted_at")


# =====================================================
# 🔑 PASSWORD MANAGEMENT
# =====================================================


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ChangePasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not check_password(old_password, request.user.password):
            return Response(
                {"detail": _("Old password incorrect")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.last_password_change = timezone.now()
        request.user.save(update_fields=["password", "last_password_change"])

        return Response(
            {"detail": _("Password updated successfully")},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            models.PasswordResetToken.objects.create(user=user, token=token)

            send_password_reset_email(user.email, token)

        return Response(
            {"detail": _("If the email exists, a reset token was sent")},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        reset_token = (
            models.PasswordResetToken.objects.filter(
                token=token_value,
                used=False,
            )
            .select_related("user")
            .first()
        )

        if not reset_token or reset_token.is_expired():
            return Response(
                {"detail": _("Invalid or expired token")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = reset_token.user
        validate_password(new_password, user)

        user.set_password(new_password)
        user.last_password_change = timezone.now()
        user.save(update_fields=["password", "last_password_change"])

        reset_token.used = True
        reset_token.save(update_fields=["used"])

        return Response(
            {"detail": _("Password reset successful")},
            status=status.HTTP_200_OK,
        )


# =====================================================
# ✉️ EMAIL VERIFICATION
# =====================================================


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.EmailVerificationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"detail": _("User not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        verification = models.EmailVerificationCode.objects.filter(
            user=user,
            code=code,
            used=False,
        ).first()

        if not verification or verification.is_expired():
            return Response(
                {"detail": _("Invalid or expired code")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        verification.used = True
        verification.save(update_fields=["used"])

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": _("Email verified successfully"),
                "user": UserResponseSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationCodeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.EmailResendSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        if user:
            # ✉️ SEND BRANDED VERIFICATION CODE
            code = "".join([secrets.choice("0123456789") for _ in range(6)])
            models.EmailVerificationCode.objects.create(user=user, code=code)

            send_branded_verification_email(user.email, code)

        return Response(
            {"detail": _("If the email exists, a new code was sent")},
            status=status.HTTP_200_OK,
        )
