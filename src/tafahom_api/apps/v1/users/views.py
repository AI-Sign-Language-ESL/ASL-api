from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    BasicUserRegistrationSerializer,
    OrganizationRegistrationSerializer,
    UserResponseSerializer,
    ChangeEmailSerializer,
    ProfileUpdateSerializer,
)
from .models import User
from tafahom_api.apps.v1.billing.models import Subscription, Plan
from tafahom_api.apps.v1.dataset.models import Contribution

# ======================================================
# 👤 BASIC USER REGISTRATION
# ======================================================


class BasicUserRegistrationView(generics.GenericAPIView):
    serializer_class = BasicUserRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pending = serializer.save()

        return Response(
            {
                "message": "Registration initiated. Please verify your email with the code sent to your inbox.",
                "email": pending.email,
            },
            status=status.HTTP_201_CREATED,
        )


# ======================================================
# 🏢 ORGANIZATION REGISTRATION
# ======================================================


class OrganizationRegistrationView(generics.GenericAPIView):
    serializer_class = OrganizationRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pending = serializer.save()

        return Response(
            {
                "message": "Registration initiated. Please verify your email with the code sent to your inbox.",
                "email": pending.email,
            },
            status=status.HTTP_201_CREATED,
        )


# ======================================================
# 👤 PROFILE (GET)
# ======================================================


class MyProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserResponseSerializer

    def get_object(self):
        return self.request.user


# ======================================================
# ✉️ CHANGE EMAIL
# ======================================================


class ChangeEmailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeEmailSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.email = serializer.validated_data["email"]
        request.user.save(update_fields=["email"])

        return Response(
            {"message": "Email updated successfully"},
            status=status.HTTP_200_OK,
        )


# ======================================================
# ✏️ UPDATE PROFILE
# ======================================================


class ProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user


# ======================================================
# 🛡️ ADMIN: DASHBOARD STATS
# ======================================================

class AdminStatsView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.db.models import Count, Q, Sum

        users = User.objects.all()
        subscriptions = Subscription.objects.all()
        contributions = Contribution.objects.all()

        stats = {
            "users": {
                "total": users.count(),
                "basic_users": users.filter(role="basic_user").count(),
                "organizations": users.filter(role="organization").count(),
                "admins": users.filter(role__in=["admin", "supervisor"]).count(),
            },
            "subscriptions": {
                "active": subscriptions.filter(status="active").count(),
            },
            "transactions": {
                "total": 0,
                "successful": 0,
            },
            "contributions": contributions.values("status").annotate(count=Count("status")).values("status", "count"),
        }

        return Response(stats)


# ======================================================
# 🛡️ ADMIN: LIST USERS
# ======================================================

class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserResponseSerializer

    def get_queryset(self):
        queryset = User.objects.all().select_related("organization_profile")

        role = self.request.query_params.get("role")
        search = self.request.query_params.get("search")

        if role:
            queryset = queryset.filter(role=role)
        if search:
            queryset = queryset.filter(email__icontains=search) | queryset.filter(username__icontains=search)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        users = list(queryset)

        # Enrich with plan and token info
        from tafahom_api.apps.v1.billing.models import Subscription, Plan
        user_data = []
        for u in users:
            data = UserResponseSerializer(u).data
            subscription = Subscription.objects.filter(user=u, status="active").first()
            data["plan"] = subscription.plan.name if subscription else None
            data["tokens_used"] = getattr(u, "tokens_used", 0)
            data["bonus_tokens"] = getattr(u, "bonus_tokens", 0)
            user_data.append(data)

        return Response(user_data)


# ======================================================
# 🛡️ ADMIN: ADD TOKENS
# ======================================================

class AdminAddTokensView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        from django.db.models import F

        user = User.objects.get(id=user_id)
        amount = request.data.get("amount", 0)
        user.bonus_tokens = F("bonus_tokens") + int(amount)
        user.save(update_fields=["bonus_tokens"])
        return Response({"message": f"Added {amount} tokens"})


# ======================================================
# 🛡️ ADMIN: REMOVE TOKENS
# ======================================================

class AdminRemoveTokensView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        from django.db.models import F

        user = User.objects.get(id=user_id)
        amount = request.data.get("amount", 0)
        user.bonus_tokens = F("bonus_tokens") - int(amount)
        user.save(update_fields=["bonus_tokens"])
        return Response({"message": f"Removed {amount} tokens"})


# ======================================================
# 🛡️ ADMIN: CHANGE PLAN
# ======================================================

class AdminChangePlanView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = User.objects.get(id=user_id)
        plan_type = request.data.get("plan_type")

        plan = Plan.objects.get(name__iexact=plan_type)
        subscription, _ = Subscription.objects.get_or_create(user=user, defaults={"status": "active", "plan": plan})
        subscription.plan = plan
        subscription.status = "active"
        subscription.save()

        return Response({"message": f"Changed plan to {plan_type}"})


# ======================================================
# 📂 MY CONTRIBUTIONS
# ======================================================

class MyContributionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tafahom_api.apps.v1.dataset.serializers import ContributionSerializer

        contributions = Contribution.objects.filter(user=request.user)
        return Response(ContributionSerializer(contributions, many=True).data)
