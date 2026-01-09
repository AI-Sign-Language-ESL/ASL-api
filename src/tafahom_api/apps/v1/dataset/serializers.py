import mimetypes
from rest_framework import serializers
from .models import DatasetContribution


MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/webm",
    "video/x-msvideo",  # avi
}
ALLOWED_EXTENSIONS = {".mp4", ".webm", ".avi"}


class DatasetContributionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetContribution
        fields = ["id", "word", "video", "status"]
        read_only_fields = ["id", "status"]

    def validate_word(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Word cannot be empty")
        return value

    def validate_video(self, file):
        if file.size > MAX_VIDEO_SIZE:
            raise serializers.ValidationError("Video too large (max 50MB).")

        ext = "." + file.name.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Unsupported video extension.")

        mime, _ = mimetypes.guess_type(file.name)
        if mime not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError("Invalid video MIME type.")

        return file


class DatasetContributionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetContribution
        fields = [
            "id",
            "word",
            "video",
            "status",
            "created_at",
        ]


class DatasetContributionActionSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
