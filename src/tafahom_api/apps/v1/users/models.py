import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("basic_user", "Basic User"),
        ("organization", "Organization"),
        ("supervisor", "Supervisor"),
        ("admin", "Admin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="basic_user")
    last_password_change = models.DateTimeField(null=True, blank=True)
    google_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    is_verified = models.BooleanField(default=False)
    organization = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        limit_choices_to={"role": "organization"},
        help_text="For basic users: the organization they belong to",
    )

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["google_id"]),
            models.Index(fields=["organization"]),
        ]

    def __str__(self):
        return self.username

    @property
    def is_organization_admin(self):
        return self.role == "organization"

    @property
    def organization_members_count(self):
        if self.role == "organization":
            return self.members.count()
        return 0


class Organization(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="organization_profile"
    )
    organization_name = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    org_code = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.org_code:
            import secrets
            self.org_code = secrets.token_hex(4).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.organization_name
