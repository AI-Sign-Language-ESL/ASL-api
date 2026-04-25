import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Meeting")
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hosted_meetings")
    meeting_code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.meeting_code})"


class Participant(models.Model):
    ROLE_CHOICES = (
        ("host", "Host"),
        ("participant", "Participant"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="participants")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="participant")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "meeting")