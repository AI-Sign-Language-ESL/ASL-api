from django.urls import path
from .views import TranslateToSignView, TranslationStatusView

app_name = "translation"
urlpatterns = [
    path("to-sign/", TranslateToSignView.as_view()),
    path("status/<int:pk>/", TranslationStatusView.as_view()),
]
