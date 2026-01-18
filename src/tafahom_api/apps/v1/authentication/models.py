from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import secrets
import pyotp
import qrcode
from io import BytesIO
import base64


class TwoFactorAuth(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="two_factor_auth",
    )

    secret_key = models.CharField(
        max_length=32, unique=True, help_text="TOTP secret key"
    )

    is_enabled = models.BooleanField(
        default=False, help_text="Wheter 2FA is currently active"
    )

    backup_codes = models.JSONField(
        default=list, help_text="List of backup codes for accout recovery"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "two_factor_auth"
        verbose_name = _("Two Factor Authentication")
        verbose_name_plural = _("Two Factor Authentications")

    def __str__(self):
        status = "Enabled" if self.is_enabled else "Disabled"
        return f"2FA for {self.user.username} - {status}"

    def generate_secret_key(self):
        self.secret_key = pyotp.random_base32()
        self.save()
        return self.secret_key

    def get_totp_uri(self):
        return pyotp.totp.TOTP(self.secret_key).provisioning_uri(
            name=self.user.email, issuer_name="TAFAHOM"
        )

    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.get_totp_uri())
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode()

    def verify_token(self, token):
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)

    def generate_backup_codes(self, count=10):
        self.backup_codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.save()
        return self.backup_codes

    def use_backup_code(self, code):
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save()
            return True
        return False


class LoginAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_attempts",
        null=True,
        blank=True,
        help_text="The user who attempted to log in",
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address from which the login attempt was made"
    )
    username = models.CharField(
        max_length=150, help_text="Username used in the login attempt"
    )
    success = models.BooleanField(
        default=False, help_text="Whether the login attempt was successful"
    )
    attempted_at = models.DateTimeField(auto_now_add=True)
    user_Agent = models.TextField(
        blank=True, help_text="User agent string of the client"
    )
    failure_reason = models.CharField(
        max_length=100, blank=True, help_text="Reason for login failure, if applicable"
    )

    class Meta:
        db_table = "login_attempts"
        ordering = ["attempted_at"]
        indexes = [
            models.Index(fields=["username", "ip_address", "-attempted_at"]),
            models.Index(fields=["user", "-attempted_at"]),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.username} - {status} - {self.attempted_at}"

    @classmethod
    def is_locked(cls, username, ip_address, max_attempts=5, lockout_duration=15):
        time_threshold = timezone.now() - timedelta(minutes=lockout_duration)

        failed_attempts = cls.objects.filter(
            username=username,
            ip_address=ip_address,
            success=False,
            attempted_at__gte=time_threshold,
        ).count()
        return failed_attempts >= max_attempts

    @classmethod
    def get_recent_attempts(cls, user, hours=24):
        time_threshold = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(user=user, attempted_at__gte=time_threshold)

    @classmethod
    def clear_old_attempts(cls, days=30):
        time_threshold = timezone.now() - timedelta(days=days)
        count, _ = cls.objects.filter(attempted_at__lt=time_threshold).delete()
        return count


class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=15)
