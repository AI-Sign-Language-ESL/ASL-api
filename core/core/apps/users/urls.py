from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, BasicUserRegistrationView, OrganizationRegistrationView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/basic/", BasicUserRegistrationView.as_view(), name="register-basic"),
    path(
        "register/organization/",
        OrganizationRegistrationView.as_view(),
        name="register-organization",
    ),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
