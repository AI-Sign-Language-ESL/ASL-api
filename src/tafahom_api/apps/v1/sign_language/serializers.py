from rest_framework import serializers
from .models import SignRecognitionHistory

class SignRecognitionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SignRecognitionHistory
        fields = ['id', 'user', 'uploaded_video', 'prediction', 'confidence', 'created_at']
        read_only_fields = ['id', 'user', 'prediction', 'confidence', 'created_at']

class SignRecognitionUploadSerializer(serializers.Serializer):
    video = serializers.FileField(required=True)
