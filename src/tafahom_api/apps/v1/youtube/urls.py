from django.urls import path
from . import views

app_name = "youtube"
urlpatterns = [
    path("translate/", views.YouTubeTranslateView.as_view(), name="translate"),
    path("upload-video/", views.YouTubeUploadVideoView.as_view(), name="upload-video"),
    path("sign-translate/", views.YouTubeSignTranslateView.as_view(), name="sign-translate"),
    path("history/", views.YouTubeTranslationHistoryView.as_view(), name="history"),
    path("transcript/", views.TranscriptCheckView.as_view(), name="transcript-check"),
    path("transcript/fetch/", views.FetchTranscriptView.as_view(), name="transcript-fetch"),
    path("process-transcript/", views.ProcessTranscriptView.as_view(), name="process-transcript"),
    path("browser-transcript/", views.BrowserTranscriptView.as_view(), name="browser-transcript"),
    path("<int:pk>/", views.YouTubeTranslationDetailView.as_view(), name="detail"),
]
