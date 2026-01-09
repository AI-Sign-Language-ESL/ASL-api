from django.contrib import admin
from .models import TwoFactorAuth, LoginAttempt, PasswordResetToken


@admin.register(TwoFactorAuth)
class TwoFactorAuthAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enabled", "created_at", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("secret_key", "backup_codes")  # Protect sensitive data


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "success", "attempted_at")
    list_filter = ("success", "attempted_at")
    search_fields = ("user__username", "ip_address", "failure_reason")
    readonly_fields = (
        "user",
        "ip_address",
        "success",
        "failure_reason",
        "attempted_at",
    )

    def has_add_permission(self, request):
        return False  # Logs should not be created manually


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "used", "is_expired_display")
    list_filter = ("used", "created_at")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)

    def is_expired_display(self, obj):
        return obj.is_expired()

    is_expired_display.boolean = True
    is_expired_display.short_description = "Expired"
