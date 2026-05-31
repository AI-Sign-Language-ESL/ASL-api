from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("contribution_submitted", "Contribution Submitted"),
        ("contribution_approved", "Contribution Approved"),
        ("contribution_rejected", "Contribution Rejected"),
        ("tokens", "Tokens"),
        ("meeting_invite", "Meeting Invite"),
        ("subscription", "Subscription"),
        ("general", "General"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default="general")
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="notifica_user_created_idx"),
            models.Index(fields=["user", "is_read"], name="notifica_user_read_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"
