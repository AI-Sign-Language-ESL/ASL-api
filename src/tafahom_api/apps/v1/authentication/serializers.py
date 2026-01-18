from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from . import models

from tafahom_api.apps.v1.users.models import User

# =========================
# 🔐 LOGIN & TOKENS
# =========================


# authentication/serializers.py


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()  # username OR email
    password = serializers.CharField(write_only=True)


class Login2FASerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    token = serializers.CharField(max_length=12)


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


# =========================
# 🛡️ TWO-FACTOR SETUP (2FA)
# =========================


class TwoFactorSetupResponseSerializer(serializers.Serializer):
    qr_code = serializers.CharField(help_text=_("Base64 encoded QR code image"))
    manual_entry_key = serializers.CharField(help_text=_("Manual entry key for TOTP"))
    is_enabled = serializers.BooleanField(help_text=_("Indicates if 2FA is enabled"))


class TwoFactorEnableSerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text=_("6-digit TOTP token"),
    )

    def validate_token(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(_("Token must contain only digits."))
        return value


class TwoFactorEnableResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    backup_codes = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("Backup recovery codes"),
    )


class TwoFactorDisableSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        help_text=_("Current account password"),
    )
    token = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text=_("6-digit TOTP token"),
    )

    def validate_token(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(_("Token must contain only digits."))
        return value


class TwoFactorVerifySerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=6,
        min_length=6,
        required=False,
        help_text=_("TOTP token"),
    )
    backup_code = serializers.CharField(
        max_length=12,
        min_length=12,
        required=False,
        help_text=_("Backup code"),
    )

    def validate(self, attrs):
        if not attrs.get("token") and not attrs.get("backup_code"):
            raise serializers.ValidationError(
                _("Either token or backup code must be provided.")
            )
        return attrs


class TwoFactorStatusSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField()
    has_backup_codes = serializers.BooleanField()
    backup_codes_count = serializers.IntegerField()


# =========================
# 🚨 LOGIN ATTEMPTS
# =========================


class LoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LoginAttempt
        fields = [
            "id",
            "username",
            "ip_address",
            "success",
            "failure_reason",
            "attempted_at",
        ]
        read_only_fields = fields


class LoginAttemptHistorySerializer(serializers.Serializer):
    total_attempts = serializers.IntegerField()
    successful_attempts = serializers.IntegerField()
    failed_attempts = serializers.IntegerField()
    recent_attempts = LoginAttemptSerializer(many=True)


# =========================
# 🔑 PASSWORD MANAGEMENT
# =========================


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
