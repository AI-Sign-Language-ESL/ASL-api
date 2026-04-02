from django.urls import path
from . import views

app_name = "social"

urlpatterns = [
    path("youtube/", views.YouTubeIntegrationView.as_view(), name="youtube"),
]
