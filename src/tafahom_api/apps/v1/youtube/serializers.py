from rest_framework import serializers
from .models import YouTubeTranslation

class YouTubeTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = YouTubeTranslation
        fields = ['id', 'youtube_url', 'transcript', 'status', 'tokens_used', 'animation_data', 'created_at', 'updated_at']

class YouTubeTranslationCreateSerializer(serializers.Serializer):
    youtube_url = serializers.URLField()

class VideoUploadSerializer(serializers.Serializer):
    video = serializers.FileField(required=False)
    video_file = serializers.FileField(required=False)
    video_id = serializers.CharField(required=False, allow_blank=True)


class TranscriptSegmentSerializer(serializers.Serializer):
    start = serializers.FloatField()
    duration = serializers.FloatField()
    text = serializers.CharField()


class TranscriptFetchSerializer(serializers.Serializer):
    video_id = serializers.CharField(max_length=20)
    language = serializers.CharField(max_length=10, required=False, default=None)

    def validate_video_id(self, value):
        import re
        if not re.match(r"^[0-9A-Za-z_-]{11}$", value):
            raise serializers.ValidationError("Invalid YouTube video ID format.")
        return value


class BrowserTranscriptSerializer(serializers.Serializer):
    video_id = serializers.CharField(max_length=20, required=False, allow_blank=True)
    title = serializers.CharField(max_length=500, required=False, allow_blank=True)
    transcript = serializers.CharField()
    segments = TranscriptSegmentSerializer(many=True, required=False)
    language = serializers.CharField(max_length=10, required=False, default='ar')

    def validate_transcript(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Transcript is too short (minimum 5 characters).")
        if len(value) > 10000:
            raise serializers.ValidationError("Transcript is too long (maximum 10,000 characters).")
        return value
