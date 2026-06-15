from django.urls import path
from .views import SignRecognitionView

app_name = "sign_language"

urlpatterns = [
    path("recognize/", SignRecognitionView.as_view(), name="sign-recognition"),
]
