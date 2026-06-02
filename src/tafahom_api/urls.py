from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.static import serve

from tafahom_api.apps.v1.translation.views import TestGlossView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("tafahom_api.apps.v1.urls")),
    path("api/v1/health/", include("tafahom_api.apps.v1.health.urls")),
    path("api/v1/sign-language/test-gloss/", TestGlossView.as_view(), name="test-gloss"),
    path("auth/", TokenObtainPairView.as_view(), name="authtoken"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="authtoken-refresh"),
    path("docs/", SpectacularSwaggerView.as_view(), name="docs"),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Directly serve media files via Django to bypass Nginx file permission issues
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
