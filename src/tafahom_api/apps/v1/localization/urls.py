from django.urls import path
from .views import (
    LanguageListView,
    SetLanguageView,
    CurrentLanguageView,
    BulkTranslationKeyView,
    TranslationKeyListView,
    TranslationKeyDetailView,
)

app_name = "localization"
urlpatterns = [
    path("languages/", LanguageListView.as_view(), name="languages"),
    path("set-language/", SetLanguageView.as_view(), name="set-language"),
    path("current-language/", CurrentLanguageView.as_view(), name="current-language"),
    path("translations/bulk/", BulkTranslationKeyView.as_view(), name="bulk"),
    # Admin
    path("keys/", TranslationKeyListView.as_view(), name="keys"),
    path("keys/<int:pk>/", TranslationKeyDetailView.as_view(), name="key-detail"),
]
