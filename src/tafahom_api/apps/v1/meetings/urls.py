from django.urls import path
from .views import (
    CreateMeetingView,
    JoinMeetingView,
    LeaveMeetingView,
    ParticipantsView,
    EndMeetingView,
)

urlpatterns = [
    path("create/", CreateMeetingView.as_view()),
    path("join/<str:code>/", JoinMeetingView.as_view()),
    path("leave/<str:code>/", LeaveMeetingView.as_view()),
    path("participants/<str:code>/", ParticipantsView.as_view()),
    path("end/<str:code>/", EndMeetingView.as_view()),
]