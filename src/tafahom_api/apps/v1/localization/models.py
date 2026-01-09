from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class TranslationKey(models.Model):
    key = models.CharField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    context = models.CharField(max_length=100, blank=True)
    text_en = models.TextField(verbose_name="English Text")
    text_ar = models.TextField(verbose_name="Arabic Text")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "translation_keys"
        verbose_name = _("Translation Key")
        verbose_name_plural = _("Translation Keys")
        ordering = ["key"]
        indexes = [models.Index(fields=["key"]), models.Index(fields=["context"])]

    def __str__(self):
        return f"{self.key} ({self.context})"

    def get_text(self, language_code="en"):
        if language_code == "ar":
            return self.text_ar
        return self.text_en
