from django.db import models
from django.conf import settings
from django.utils import timezone

from tafahom_api.common.enums import (
    DATASET_CONTRIBUTION_STATUS,
    DATASET_STATUS_TRANSITIONS,
)


class InvalidDatasetStatusTransition(Exception):
    pass


class DatasetContribution(models.Model):
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dataset_contributions",
    )

    word = models.CharField(max_length=200)

    video = models.FileField(
        upload_to="dataset/videos/%Y/%m/%d/",
    )

    status = models.CharField(
        max_length=20,
        choices=DATASET_CONTRIBUTION_STATUS,
        default="pending",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_dataset_contributions",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dataset_contributions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["contributor"]),
            models.Index(fields=["created_at"]),
        ]

    # =========================
    # 🔐 STATE MACHINE
    # =========================
    def _transition_to(self, new_status, reviewer=None):
        allowed = DATASET_STATUS_TRANSITIONS.get(self.status, set())

        if new_status not in allowed:
            raise InvalidDatasetStatusTransition(
                f"Cannot transition from '{self.status}' to '{new_status}'"
            )

        self.status = new_status

        if reviewer:
            self.reviewer = reviewer
            self.reviewed_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "reviewer",
                "reviewed_at",
            ]
        )

    # Public domain actions
    def mark_processing(self):
        self._transition_to("processing")

    def approve(self, reviewer):
        self._transition_to("approved", reviewer=reviewer)

    def reject(self, reviewer):
        self._transition_to("rejected", reviewer=reviewer)

    def mark_failed(self):
        self._transition_to("failed")

    def __str__(self):
        return f"{self.word} | {self.status}"
