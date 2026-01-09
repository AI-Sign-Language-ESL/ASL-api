import secrets
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.mail import send_mail

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from tafahom_api.apps.v1.users.models import User
from .services.token_service import refresh_access_token
from .services.google_auth import authenticate_with_google
from . import models, serializers

# You may need to import UserResponseSerializer if you want to return user data on login
# Ideally, move shared serializers to a 'common' place, or import from users
from tafahom_api.apps.v1.users.serializers import UserResponseSerializer


# =========================
# 🔐 LOGIN (EMAIL/PASSWORD)
# =========================


class LoginView(generics.GenericAPIView):
    serializer_class = serializers.LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(
            request,
            username=user.username,
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }
        )


# =========================
# 🔐 LOGIN WITH 2FA
# =========================


class Login2FAView(generics.GenericAPIView):
    serializer_class = serializers.Login2FASerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        token = serializer.validated_data["token"]

        try:
            user = User.objects.get(id=user_id)
            two_fa = models.TwoFactorAuth.objects.get(user=user)
        except (User.DoesNotExist, models.TwoFactorAuth.DoesNotExist):
            return Response(
                {"detail": "Invalid user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not two_fa.verify_token(token) and not two_fa.use_backup_code(token):
            return Response(
                {"detail": "Invalid authentication code"},
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
            }
        )


# =========================
# 🌐 GOOGLE LOGIN
# =========================


class GoogleLoginView(APIView):
    permission_classes = []

    def post(self, request):
        token = request.data.get("token")

        try:
            user = authenticate_with_google(token)
        except Exception as e:
            return Response(
                {"detail": str(e)},
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


# =========================
# 🔄 REFRESH TOKEN
# =========================


class RefreshTokenView(APIView):
    pass


# =========================
# 🛡️ TWO FACTOR SETUP
# =========================


class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.TwoFactorSetupResponseSerializer

    def post(self, request):
        two_fa, _ = models.TwoFactorAuth.objects.get_or_create(user=request.user)

        if not two_fa.secret_key:
            two_fa.generate_secret_key()

        qr_code = two_fa.generate_qr_code()

        serializer = self.serializer_class(
            {
                "qr_code": f"data:image/png;base64,{qr_code}",
                "manual_entry_key": two_fa.secret_key,
                "is_enabled": two_fa.is_enabled,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class TwoFactorEnableView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.TwoFactorEnableSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        two_fa = models.TwoFactorAuth.objects.filter(user=request.user).first()
        if not two_fa or not two_fa.verify_token(serializer.validated_data["token"]):
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

        if not authenticate(
            username=request.user.username,
            password=serializer.validated_data["password"],
        ):
            return Response(
                {"detail": _("Invalid password")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        two_fa = models.TwoFactorAuth.objects.filter(user=request.user).first()
        if not two_fa or not two_fa.verify_token(serializer.validated_data["token"]):
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


# =========================
# 🚨 LOGIN ATTEMPTS
# =========================


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


# =========================
# 🔑 PASSWORD MANAGEMENT
# =========================


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ChangePasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        if not check_password(
            serializer.validated_data["old_password"],
            request.user.password,
        ):
            return Response(
                {"detail": _("Old password incorrect")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.last_password_change = timezone.now()
        request.user.save(update_fields=["password", "last_password_change"])

        return Response(
            {"detail": _("Password updated successfully")},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    permission_classes = []
    serializer_class = serializers.PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if user:
            token = secrets.token_urlsafe(32)
            models.PasswordResetToken.objects.create(user=user, token=token)

            frontend_base = getattr(settings, "FRONTEND_URL", "")
            if frontend_base:
                reset_link = f"{frontend_base.rstrip('/')}/reset-password?token={token}"
            else:
                reset_link = request.build_absolute_uri(
                    f"/password-reset/confirm/?token={token}"
                )

            subject = _("Password reset request")
            message = _(
                "We received a request to reset your password. Use the link below to reset it:\n\n{link}\n\nIf you did not request this, you can ignore this email."
            ).format(link=reset_link)

            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
            try:
                send_mail(
                    subject, message, from_email, [user.email], fail_silently=True
                )
            except Exception:
                pass

        return Response(
            {"detail": _("If the email exists, a reset link was sent")},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = []
    serializer_class = serializers.PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        reset_token = (
            models.PasswordResetToken.objects.select_related("user")
            .filter(token=token_value, used=False)
            .first()
        )

        if not reset_token:
            return Response(
                {"detail": _("Invalid or used token")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reset_token.is_expired():
            return Response(
                {"detail": _("Token expired")},
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
