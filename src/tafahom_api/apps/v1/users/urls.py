from django.urls import path
from . import views, admin_views

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

    # Admin - Users
    path("admin/users/", admin_views.AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", admin_views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<int:user_id>/change-plan/", admin_views.AdminChangeUserPlanView.as_view(), name="admin-change-plan"),
    path("admin/users/<int:user_id>/add-tokens/", admin_views.AdminAddTokensView.as_view(), name="admin-add-tokens"),
    path("admin/users/<int:user_id>/remove-tokens/", admin_views.AdminRemoveTokensView.as_view(), name="admin-remove-tokens"),

    # Admin - Transactions
    path("admin/transactions/", admin_views.AdminTransactionsView.as_view(), name="admin-transactions"),

    # Admin - Stats
    path("admin/dashboard-stats/", admin_views.AdminDashboardStatsView.as_view(), name="admin-dashboard-stats"),

    # Supervisor - Dataset Contributions
    path("supervisor/contributions/", admin_views.SupervisorContributionsView.as_view(), name="supervisor-contributions"),
    path("supervisor/contributions/<int:contribution_id>/approve/", admin_views.SupervisorApproveView.as_view(), name="supervisor-approve"),
    path("supervisor/contributions/<int:contribution_id>/reject/", admin_views.SupervisorRejectView.as_view(), name="supervisor-reject"),

    # Organization Admin - Manage Members
    path("org/members/", admin_views.OrgMembersView.as_view(), name="org-members"),
    path("org/members/<int:member_id>/remove/", admin_views.OrgMembersView.as_view(), name="org-remove-member"),
    path("org/members/<int:member_id>/add-tokens/", admin_views.OrgAddTokensView.as_view(), name="org-add-tokens"),
    path("org/members/<int:member_id>/remove-tokens/", admin_views.OrgRemoveTokensView.as_view(), name="org-remove-tokens"),
    path("org/profile/", admin_views.OrgProfileView.as_view(), name="org-profile"),
]
