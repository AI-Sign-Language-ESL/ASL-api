from django.urls import path
from . import views

app_name = "youtube"
urlpatterns = [
    path("translate/", views.YouTubeTranslateView.as_view(), name="translate"),
    path("sign-translate/", views.YouTubeSignTranslateView.as_view(), name="sign-translate"),
    path("history/", views.YouTubeTranslationHistoryView.as_view(), name="history"),
    path("<int:pk>/", views.YouTubeTranslationDetailView.as_view(), name="detail"),
]
