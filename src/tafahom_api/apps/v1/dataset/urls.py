from django.urls import path
from . import views

app_name = "dataset"  # 👈 Added namespace for consistency

urlpatterns = [
    path(
        "contributions/",
        views.DatasetContributionCreateView.as_view(),
        name="dataset-contribution-create",
    ),
    path(
        "contributions/me/",
        views.MyDatasetContributionsView.as_view(),
        name="my-dataset-contributions",
    ),
    path(
        "admin/contributions/pending/",
        views.PendingDatasetContributionsView.as_view(),
        name="pending-dataset-contributions",
    ),
    path(
        "admin/contributions/<int:pk>/approve/",
        views.ApproveDatasetContributionView.as_view(),
        name="approve-dataset-contribution",
    ),
    path(
        "admin/contributions/<int:pk>/reject/",
        views.RejectDatasetContributionView.as_view(),
        name="reject-dataset-contribution",
    ),
]
