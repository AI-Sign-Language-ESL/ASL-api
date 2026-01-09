from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include, URLPattern, URLResolver
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("tafahom_api.apps.v1.urls")),
    path("auth/", TokenObtainPairView.as_view(), name="authtoken"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="authtoken-refresh"),
    path("docs/", SpectacularSwaggerView.as_view(), name="docs"),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
