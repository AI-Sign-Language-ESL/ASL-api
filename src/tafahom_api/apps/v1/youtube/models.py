from django.db import models
from django.conf import settings

class YouTubeTranslation(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    SOURCE_CHOICES = [
        ("transcript", "Transcript"),
        ("yt_dlp", "yt-dlp"),
        ("upload", "Upload"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="youtube_translations",
    )
    youtube_url = models.URLField()
    transcript = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    tokens_used = models.PositiveIntegerField(default=15)
    animation_data = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "youtube_translations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.youtube_url} ({self.status})"
