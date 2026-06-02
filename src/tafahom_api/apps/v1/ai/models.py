import uuid
from django.conf import settings
from django.db import models

from tafahom_api.common.enums import CONVERSATION_STATUS, MESSAGE_ROLES


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

    tokens_used = models.PositiveIntegerField(default=1)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_airequest"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["service"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.service} | {self.status} | {self.latency_ms}ms"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fehm_conversations",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=CONVERSATION_STATUS,
        default="active",
    )
    meta_data = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fehm_conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.user.username})"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=MESSAGE_ROLES)
    content = models.TextField()
    tokens_used = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=50, blank=True, default="")
    extra_data = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fehm_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class MultiModelTranslationMetric(models.Model):
    """
    Logs multi-model competition for gloss-to-text translations.
    Stores latencies and outputs for mbart, mt5, and nllb, and the winner.
    """
    gloss = models.TextField()
    
    winner_model = models.CharField(max_length=50)
    winner_latency_ms = models.PositiveIntegerField()
    
    mbart_output = models.TextField(blank=True, null=True)
    mbart_latency_ms = models.PositiveIntegerField(blank=True, null=True)
    
    mt5_output = models.TextField(blank=True, null=True)
    mt5_latency_ms = models.PositiveIntegerField(blank=True, null=True)
    
    nllb_output = models.TextField(blank=True, null=True)
    nllb_latency_ms = models.PositiveIntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "ai_multimodel_translation_metric"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["winner_model"]),
            models.Index(fields=["created_at"]),
        ]
        
    def __str__(self):
        return f"Metric: {self.gloss[:30]} | Winner: {self.winner_model} ({self.winner_latency_ms}ms)"
