from django.urls import path
from . import views

app_name = "translation"
urlpatterns = [
    path(
        "requests/",
        views.TranslationRequestCreateView.as_view(),
        name="translation-request-create",
    ),
    path(
        "requests/me/",
        views.MyTranslationRequestsView.as_view(),
        name="my-translation-requests",
    ),
    path("to-sign/", views.TranslateToSignView.as_view()),
    path("unity-sign/", views.UnityTranslateView.as_view()),
    path("status/<int:pk>/", views.TranslationStatusView.as_view()),

    path("speech-to-text/", views.SpeechToTextView.as_view()),
    path("youtube-translate/", views.YouTubeTranslateView.as_view(), name="youtube-translate"),
    path("translate/", views.TranslationAPIView.as_view(), name="hybrid-translate"),
    path("requests/<int:pk>/save/", views.SaveTranslationHistoryView.as_view(), name="save-history"),
]
####