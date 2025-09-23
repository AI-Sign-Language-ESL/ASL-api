from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("basic_user", "Basic User"),
        ("organization", "Organization"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="basic_user")

    class Meta:
        db_table = "users"  # Add this to avoid table name conflicts

    def __str__(self):
        return self.username


class Organization(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="organization"
    )
    organization_name = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.organization_name
