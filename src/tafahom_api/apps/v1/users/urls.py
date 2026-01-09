from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    # Registration
    path(
        "register/basic/",
        views.BasicUserRegistrationView.as_view(),
        name="register-basic",
    ),
    path(
        "register/organization/",
        views.OrganizationRegistrationView.as_view(),
        name="register-organization",
    ),
    # Profile Management
    path("me/", views.MyProfileView.as_view(), name="my-profile"),
    path("me/update/", views.ProfileUpdateView.as_view(), name="profile-update"),
    path("me/email/", views.ChangeEmailView.as_view(), name="change-email"),
]
