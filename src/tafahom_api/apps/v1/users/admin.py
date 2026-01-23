from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with extra fields (role, google_id)
    """

    fieldsets = tuple(BaseUserAdmin.fieldsets) + (
        ("Extra Info", {"fields": ("role", "google_id")}),
    )

    add_fieldsets = tuple(BaseUserAdmin.add_fieldsets) + (
        (None, {"fields": ("email", "role")}),
    )

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("username",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name",
        "activity_type",
        "job_title",
        "user",
    )

    list_filter = ("activity_type",)

    search_fields = (
        "organization_name",
        "user__username",
        "user__email",
    )

    raw_id_fields = ("user",)
