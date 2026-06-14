from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import SignRecognitionUploadSerializer, SignRecognitionHistorySerializer
from .models import SignRecognitionHistory
from .services.ai_service import predict_sign

class SignRecognitionView(APIView):
    """
    API endpoint to upload a video for sign language recognition.
    """
    parser_classes = (MultiPartParser, FormParser)
    
    # Optional: depending on requirements, we can allow unauthenticated access
    # or enforce authentication. For now, we allow any to ensure it works
    # easily in development.
    permission_classes = [] 

    def post(self, request, *args, **kwargs):
        serializer = SignRecognitionUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_video = serializer.validated_data['video']
            
            # Here we would normally save the video temporarily or permanently
            # before passing to the AI model. For now, we just pass the path or object.
            # We'll save the history instance first to get the file saved.
            
            # Since user can be null if not authenticated
            user = request.user if request.user.is_authenticated else None
            
            history = SignRecognitionHistory(
                user=user,
                uploaded_video=uploaded_video,
                prediction="",
                confidence=0.0
            )
            history.save()
            
            # Call the AI service
            try:
                # pass the saved file path
                result = predict_sign(history.uploaded_video.path)
                
                # Update history with results
                history.prediction = result.get('prediction', 'UNKNOWN')
                history.confidence = result.get('confidence', 0.0)
                history.save()
                
                response_serializer = SignRecognitionHistorySerializer(history)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                history.delete() # cleanup on failure
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        """
        Optional: Return the user's history
        """
        if request.user.is_authenticated:
            history = SignRecognitionHistory.objects.filter(user=request.user)
            serializer = SignRecognitionHistorySerializer(history, many=True)
            return Response(serializer.data)
        return Response({"error": "Authentication required to view history"}, status=status.HTTP_401_UNAUTHORIZED)
