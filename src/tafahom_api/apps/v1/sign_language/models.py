from django.db import models
from django.conf import settings

class SignRecognitionHistory(models.fields.related.ForeignKey):
    # Just to clear up the linter, actually we will extend models.Model
    pass

class SignRecognitionHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sign_recognition_history",
        null=True,  # Allow null if users can test without logging in
        blank=True
    )
    uploaded_video = models.FileField(upload_to='sign_recognition_videos/')
    prediction = models.CharField(max_length=255)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Sign Recognition Histories"
        ordering = ['-created_at']

    def __str__(self):
        user_display = self.user.username if self.user else "Anonymous"
        return f"{user_display} - {self.prediction} ({self.confidence:.2f})"
