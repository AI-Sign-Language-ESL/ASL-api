from django.conf import settings
from django.db import models


class AIRequest(models.Model):
    """
    Logs a single AI API request (CV / NLP / Speech)
    """

    SERVICE_CHOICES = (
        ("cv", "Computer Vision"),
        ("nlp", "NLP"),
        ("speech", "Speech"),
    )

    STATUS_CHOICES = (
        ("success", "Success"),
        ("failed", "Failed"),
        ("timeout", "Timeout"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_requests",
    )

    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    endpoint = models.CharField(max_length=100)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    latency_ms = models.PositiveIntegerField(help_text="Latency in milliseconds")

    credits_used = models.PositiveIntegerField(default=1)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["service"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.service} | {self.status} | {self.latency_ms}ms"
