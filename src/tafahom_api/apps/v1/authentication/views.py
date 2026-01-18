import secrets
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail

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
# 🔐 LOGIN (USERNAME OR EMAIL)
# =====================================================


class LoginView(generics.GenericAPIView):
    serializer_class = serializers.LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        identifier = data["identifier"]
        password = data["password"]

        try:
            user = User.objects.get(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        except User.DoesNotExist:
            return Response(
                {"detail": _("Invalid credentials")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        authenticated_user = authenticate(
            request,
            username=user.username,
            password=password,
        )

        if authenticated_user is None:
            return Response(
                {"detail": _("Invalid credentials")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(authenticated_user)

        return Response(
            {
                "user": UserResponseSerializer(authenticated_user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
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

        data = serializer.validated_data
        user_id = data["user_id"]
        token = data["token"]

        try:
            user = User.objects.get(id=user_id)
            two_fa = models.TwoFactorAuth.objects.get(user=user)
        except (User.DoesNotExist, models.TwoFactorAuth.DoesNotExist):
            return Response(
                {"detail": _("Invalid user")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (two_fa.verify_token(token) or two_fa.use_backup_code(token)):
            return Response(
                {"detail": _("Invalid authentication code")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# 🌐 GOOGLE LOGIN
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

        try:
            user = authenticate_with_google(token)
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# 🔄 REFRESH TOKEN (FIXED — WAS UNREACHABLE)
# =====================================================


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.RefreshTokenSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        refresh_token = data["refresh_token"]

        try:
            refresh = RefreshToken(refresh_token)
            return Response(
                {"access": str(refresh.access_token)},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": _("Invalid refresh token")},
                status=status.HTTP_400_BAD_REQUEST,
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

        data = serializer.validated_data
        token = data["token"]

        two_fa = models.TwoFactorAuth.objects.filter(user=request.user).first()
        if not two_fa or not two_fa.verify_token(token):
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

        data = serializer.validated_data
        password = data["password"]
        token = data["token"]

        if authenticate(username=request.user.username, password=password) is None:
            return Response(
                {"detail": _("Invalid password")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        two_fa = models.TwoFactorAuth.objects.filter(user=request.user).first()
        if not two_fa or not two_fa.verify_token(token):
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
# 🚨 LOGIN ATTEMPTS
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

        data = serializer.validated_data
        old_password = data["old_password"]
        new_password = data["new_password"]

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
        user = User.objects.filter(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            models.PasswordResetToken.objects.create(user=user, token=token)

            frontend_base = getattr(settings, "FRONTEND_URL", "")
            reset_link = (
                f"{frontend_base.rstrip('/')}/reset-password?token={token}"
                if frontend_base
                else request.build_absolute_uri(
                    f"/password-reset/confirm/?token={token}"
                )
            )

            send_mail(
                _("Password reset request"),
                _("We received a password reset request.\n\n{link}").format(
                    link=reset_link
                ),
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [user.email],
                fail_silently=True,
            )

        return Response(
            {"detail": _("If the email exists, a reset link was sent")},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        token_value = data["token"]
        new_password = data["new_password"]

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
