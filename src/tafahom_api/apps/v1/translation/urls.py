from django.urls import path
from . import views

app_name = "translation"
urlpatterns = [
    path(
        "sign-languages/", views.SignLanguageListView.as_view(), name="sign-languages"
    ),
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
    path("status/<int:pk>/", views.TranslationStatusView.as_view()),

    path("speech-to-text/", views.SpeechToTextView.as_view()),

]
####