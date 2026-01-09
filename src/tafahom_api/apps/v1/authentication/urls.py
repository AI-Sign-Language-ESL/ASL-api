from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

app_name = "authentication"

urlpatterns = [
    # Login & Tokens
    path("login/", views.LoginView.as_view(), name="login"),
    path("login/2fa/", views.Login2FAView.as_view(), name="login-2fa"),
    path("login/google/", views.GoogleLoginView.as_view(), name="login-google"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # Two-Factor Authentication (Setup & Management)
    path("2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/enable/", views.TwoFactorEnableView.as_view(), name="2fa-enable"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa-disable"),
    # Password Management
    path(
        "password/change/", views.ChangePasswordView.as_view(), name="password-change"
    ),
    path(
        "password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    # Security / Monitoring
    path(
        "login/attempts/", views.MyLoginAttemptsView.as_view(), name="my-login-attempts"
    ),
    path(
        "login/attempts/all/",
        views.AllLoginAttemptsView.as_view(),
        name="all-login-attempts",
    ),
]
