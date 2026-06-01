from rest_framework import serializers
from .models import YouTubeTranslation

class YouTubeTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = YouTubeTranslation
        fields = ['id', 'youtube_url', 'transcript', 'status', 'tokens_used', 'animation_data', 'created_at', 'updated_at']

class YouTubeTranslationCreateSerializer(serializers.Serializer):
    youtube_url = serializers.URLField()

class VideoUploadSerializer(serializers.Serializer):
    video_file = serializers.FileField()
