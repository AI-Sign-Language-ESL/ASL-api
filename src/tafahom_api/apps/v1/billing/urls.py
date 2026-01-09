from django.urls import path
from . import views

app_name = "billing"  # Added namespace for consistent reverse lookups

urlpatterns = [
    path(
        "my-subscription/", views.MySubscriptionView.as_view(), name="my-subscription"
    ),
    path("plans/", views.SubscriptionPlanListView.as_view(), name="plan-list"),
    path("subscribe/", views.SubscribeView.as_view(), name="subscribe"),
    path("cancel/", views.CancelSubscriptionView.as_view(), name="cancel-subscription"),
]
