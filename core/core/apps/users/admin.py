from django.contrib import admin
from .models import User, Organization


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role")
    list_filter = ("role",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "activity_type", "job_title", "user")
    list_filter = ("activity_type",)
