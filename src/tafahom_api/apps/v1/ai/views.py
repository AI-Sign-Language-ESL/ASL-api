from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse

from .serializers import TTSSerializer
from .clients.text_to_speech_client import TextToSpeechClient


class TextToSpeechView(APIView):
    """
    POST /api/tts/generate/
    """

    async def post(self, request):
        serializer = TTSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        tts_client = TextToSpeechClient()

        try:
            audio = await tts_client.text_to_speech(
                text=data["text"],
                voice_id=data["voice_id"],
                stability=data["stability"],
                similarity_boost=data["similarity_boost"],
            )
        except Exception:
            return Response(
                {"error": "Text-to-speech service failed"},
                status=502,
            )

        return HttpResponse(
            audio,
            content_type="audio/mpeg",
        )
