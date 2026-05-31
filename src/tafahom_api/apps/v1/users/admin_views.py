from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.utils import timezone
from django.db.models import Q, Count, Sum

from .models import User, Organization
from .serializers import UserResponseSerializer
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan, TokenTransaction
from tafahom_api.apps.v1.billing.serializers import SubscriptionPlanSerializer
from tafahom_api.apps.v1.dataset.models import DatasetContribution
from tafahom_api.common.enums import DATASET_CONTRIBUTION_STATUS
from tafahom_api.apps.v1.billing.models import PaymentTransaction
from tafahom_api.apps.v1.billing.services import reward_dataset_contribution
from tafahom_api.apps.v1.billing.models import Subscription


class IsAdminOrSupervisor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.role in ["admin", "supervisor"]
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.role == "admin"
        )


class IsOrganizationAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "organization"


# ======================================================
# 👥 ADMIN - USER MANAGEMENT
# ======================================================


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserResponseSerializer

    def get_queryset(self):
        queryset = User.objects.select_related("subscription__plan", "organization").all()
        role = self.request.query_params.get("role")
        search = self.request.query_params.get("search")

        if role:
            queryset = queryset.filter(role=role)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AdminUserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserResponseSerializer
    queryset = User.objects.all()


# ======================================================
# 💳 ADMIN - PLAN MANAGEMENT
# ======================================================


class AdminChangeUserPlanView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        plan_type = request.data.get("plan_type")
        if not plan_type:
            return Response({"detail": "plan_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        if user.role == "organization" and plan_type != "enterprise":
            return Response(
                {"detail": "Organizations can only subscribe to the Enterprise plan."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(plan_type=plan_type)
        except SubscriptionPlan.DoesNotExist:
            return Response({"detail": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

        subscription, created = Subscription.objects.get_or_create(
            user=user,
            defaults={"plan": plan, "status": "active"}
        )

        if not created:
            subscription.plan = plan
            subscription.save(update_fields=["plan"])

        return Response({
            "message": f"User plan updated to {plan.name}",
            "user": UserResponseSerializer(user).data
        })


class AdminSubscriptionStatusView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status not in ["active", "cancelled", "expired", "pending"]:
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        subscription = getattr(user, 'subscription', None)
        if not subscription:
            return Response({"detail": "User has no subscription"}, status=status.HTTP_400_BAD_REQUEST)

        subscription.status = new_status
        subscription.save(update_fields=["status"])

        return Response({
            "message": f"Subscription status changed to {new_status}",
            "subscription_status": subscription.status
        })


class AdminChangeUserRoleView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        new_role = request.data.get("role")
        if new_role not in ["basic_user", "organization", "supervisor", "admin"]:
            return Response({"detail": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

        user.role = new_role
        user.save(update_fields=["role"])

        return Response({
            "message": f"User role updated to {new_role}",
            "user": UserResponseSerializer(user).data
        })


class AdminPendingOrganizationsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from tafahom_api.apps.v1.authentication.models import PendingRegistration
        pending = PendingRegistration.objects.filter(
            registration_type="organization",
            is_verified=True
        )
        data = []
        for p in pending:
            data.append({
                "id": p.id,
                "email": p.email,
                "username": p.username,
                "organization_name": p.organization_name,
                "activity_type": p.activity_type,
                "created_at": p.created_at,
            })
        return Response(data)

    def post(self, request, pending_id):
        """Admin approves and creates the organization account"""
        from tafahom_api.apps.v1.authentication.models import PendingRegistration
        try:
            pending = PendingRegistration.objects.get(
                id=pending_id,
                registration_type="organization",
                is_verified=True
            )
        except PendingRegistration.DoesNotExist:
            return Response(
                {"detail": "Pending organization not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create the organization user
        user = pending.create_organization_user()
        pending.delete()

        return Response({
            "message": f"Organization {user.organization_profile.organization_name} created successfully",
            "user": UserResponseSerializer(user).data
        })


# ======================================================
# 🪙 ADMIN - TOKEN MANAGEMENT
# ======================================================


class AdminAddTokensView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get("amount", 0)
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "Amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        subscription = getattr(user, 'subscription', None)
        if not subscription:
            return Response({"detail": "User has no subscription"}, status=status.HTTP_400_BAD_REQUEST)

        subscription.bonus_tokens += amount
        subscription.save(update_fields=["bonus_tokens"])

        TokenTransaction.objects.create(
            user=user,
            subscription=subscription,
            amount=amount,
            transaction_type="earned",
            reason=request.data.get("reason", "Admin added tokens")
        )

        return Response({
            "message": f"Added {amount} tokens to user",
            "bonus_tokens": subscription.bonus_tokens
        })


class AdminRemoveTokensView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get("amount", 0)
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "Amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        subscription = getattr(user, 'subscription', None)
        if not subscription:
            return Response({"detail": "User has no subscription"}, status=status.HTTP_400_BAD_REQUEST)

        subscription.bonus_tokens = max(0, subscription.bonus_tokens - amount)
        subscription.save(update_fields=["bonus_tokens"])

        TokenTransaction.objects.create(
            user=user,
            subscription=subscription,
            amount=-amount,
            transaction_type="used",
            reason=request.data.get("reason", "Admin removed tokens")
        )

        return Response({
            "message": f"Removed {amount} tokens from user",
            "bonus_tokens": subscription.bonus_tokens
        })


# ======================================================
# 💰 ADMIN - PAYMENT/TRANSACTION VIEW
# ======================================================


class AdminTransactionsView(generics.ListAPIView):
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        queryset = TokenTransaction.objects.select_related("user", "subscription__plan").all()
        user_id = request.query_params.get("user_id")
        transaction_type = request.query_params.get("type")

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        transactions = []
        for tx in queryset[:100]:
            transactions.append({
                "id": tx.id,
                "user": tx.user.username,
                "user_email": tx.user.email,
                "amount": tx.amount,
                "type": tx.transaction_type,
                "reason": tx.reason,
                "created_at": tx.created_at,
            })
        return Response(transactions)


class AdminPaymentTransactionsView(generics.ListAPIView):
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        queryset = PaymentTransaction.objects.select_related("user", "subscription").all()
        user_id = request.query_params.get("user_id")
        status_filter = request.query_params.get("status")

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        transactions = []
        for tx in queryset[:100]:
            transactions.append({
                "id": tx.id,
                "transaction_id": tx.transaction_id,
                "user": tx.user.username,
                "user_email": tx.user.email,
                "amount": tx.amount,
                "currency": tx.currency,
                "status": tx.status,
                "provider": tx.provider,
                "payment_method": tx.payment_method,
                "created_at": tx.created_at,
            })
        return Response(transactions)


# ======================================================
# 📊 ADMIN - DASHBOARD STATS
# ======================================================


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        total_users = User.objects.count()
        total_basic = User.objects.filter(role="basic_user").count()
        total_org = User.objects.filter(role="organization").count()
        total_admins = User.objects.filter(role="admin").count()
        
        from tafahom_api.apps.v1.authentication.models import PendingRegistration
        pending_orgs = PendingRegistration.objects.filter(registration_type="organization", is_verified=True).count()

        active_subscriptions = Subscription.objects.filter(status="active").count()

        total_transactions = TokenTransaction.objects.count()
        successful_transactions = TokenTransaction.objects.filter(amount__gt=0).count()

        recent_contributions = DatasetContribution.objects.values("status").annotate(count=Count("id"))

        return Response({
            "users": {
                "total": total_users,
                "basic_users": total_basic,
                "organizations": total_org,
                "pending_organizations": pending_orgs,
                "admins": total_admins,
            },
            "subscriptions": {
                "active": active_subscriptions,
            },
            "transactions": {
                "total": total_transactions,
                "successful": successful_transactions,
            },
            "contributions": list(recent_contributions),
        })


# ======================================================
# 👁️ SUPERVISOR - DATASET CONTRIBUTIONS
# ======================================================


class SupervisorContributionsView(generics.ListAPIView):
    permission_classes = [IsAdminOrSupervisor]

    def list(self, request, *args, **kwargs):
        queryset = DatasetContribution.objects.select_related("contributor").all()
        status_filter = request.query_params.get("status")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        contributions = []
        for contrib in queryset[:100]:
            contributions.append({
                "id": contrib.id,
                "word": contrib.word,
                "contributor": contrib.contributor.username,
                "contributor_email": contrib.contributor.email,
                "status": contrib.status,
                "video_url": contrib.video.url if contrib.video else None,
                "reviewer": contrib.reviewer.username if contrib.reviewer else None,
                "reviewed_at": contrib.reviewed_at,
                "created_at": contrib.created_at,
            })
        return Response(contributions)


class SupervisorApproveView(APIView):
    permission_classes = [IsAdminOrSupervisor]

    def post(self, request, contribution_id):
        try:
            contrib = DatasetContribution.objects.get(id=contribution_id)
        except DatasetContribution.DoesNotExist:
            return Response({"detail": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        if contrib.status != "pending":
            return Response({"detail": "Can only approve pending contributions"}, status=status.HTTP_400_BAD_REQUEST)

        contrib.status = "approved"
        contrib.reviewer = request.user
        contrib.reviewed_at = timezone.now()
        contrib.save(update_fields=["status", "reviewer", "reviewed_at"])

        from tafahom_api.apps.v1.billing.services import reward_dataset_contribution
        from tafahom_api.apps.v1.billing.models import Subscription

        # Get or create subscription for the contributor to ensure we can reward them
        subscription, _ = Subscription.objects.get_or_create(
            user=contrib.contributor,
            defaults={"status": "active"}
        )
        reward_dataset_contribution(subscription)

        from tafahom_api.common.emails import send_contribution_status_email
        send_contribution_status_email(contrib.contributor.email, contrib.word, "approved")

        # Create in-app notification
        from tafahom_api.apps.v1.notifications.models import Notification
        Notification.objects.create(
            user=contrib.contributor,
            type="contribution_approved",
            title="Contribution Approved! 🎉",
            message=f'Your video for "{contrib.word}" was approved. +10 bonus tokens added to your account!',
            action_url="/dataset",
        )

        return Response({"message": "Contribution approved", "status": contrib.status})


class SupervisorRejectView(APIView):
    permission_classes = [IsAdminOrSupervisor]

    def post(self, request, contribution_id):
        try:
            contrib = DatasetContribution.objects.get(id=contribution_id)
        except DatasetContribution.DoesNotExist:
            return Response({"detail": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        if contrib.status != "pending":
            return Response({"detail": "Can only reject pending contributions"}, status=status.HTTP_400_BAD_REQUEST)

        contrib.status = "rejected"
        contrib.reviewer = request.user
        contrib.reviewed_at = timezone.now()
        contrib.save(update_fields=["status", "reviewer", "reviewed_at"])

        from tafahom_api.common.emails import send_contribution_status_email
        send_contribution_status_email(contrib.contributor.email, contrib.word, "rejected")

        # Create in-app notification
        from tafahom_api.apps.v1.notifications.models import Notification
        Notification.objects.create(
            user=contrib.contributor,
            type="contribution_rejected",
            title="Contribution Update",
            message=f'Your video for "{contrib.word}" was not approved. Please review our guidelines and try again.',
            action_url="/dataset",
        )

        return Response({"message": "Contribution rejected", "status": contrib.status})


# ======================================================
# 🏢 ORGANIZATION ADMIN - MANAGE MEMBERS
# ======================================================


class OrgMembersView(APIView):
    permission_classes = [IsOrganizationAdmin]

    def get(self, request):
        members = User.objects.filter(organization=request.user).select_related("subscription__plan")
        data = []
        for member in members:
            member_data = UserResponseSerializer(member).data
            if hasattr(member, 'subscription') and member.subscription:
                member_data['plan'] = member.subscription.plan.plan_type
                member_data['tokens_used'] = member.subscription.tokens_used
                member_data['bonus_tokens'] = member.subscription.bonus_tokens
            data.append(member_data)
        return Response(data)

    def delete(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, organization=request.user)
        except User.DoesNotExist:
            return Response({"detail": "Member not found"}, status=status.HTTP_404_NOT_FOUND)

        member.organization = None
        member.save(update_fields=["organization"])
        return Response({"message": "Member removed from organization"})


class OrgProfileView(APIView):
    permission_classes = [IsOrganizationAdmin]

    def get(self, request):
        org_profile = request.user.organization_profile
        return Response({
            "organization_name": org_profile.organization_name,
            "org_code": org_profile.org_code,
            "activity_type": org_profile.activity_type,
            "members_count": request.user.organization_members_count,
        })


class OrgAddTokensView(APIView):
    permission_classes = [IsOrganizationAdmin]

    def post(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, organization=request.user)
        except User.DoesNotExist:
            return Response({"detail": "Member not found"}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get("amount", 0)
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "Amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        admin_subscription = getattr(request.user, 'subscription', None)
        if not admin_subscription:
            return Response({"detail": "You do not have an active subscription"}, status=status.HTTP_400_BAD_REQUEST)

        # Check total available tokens (weekly remaining + bonus)
        admin_remaining = admin_subscription.remaining_tokens()
        if admin_remaining < amount:
            return Response(
                {"detail": f"Not enough tokens. Your current balance is {admin_remaining}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        member_subscription = getattr(member, 'subscription', None)
        if not member_subscription:
            # Create subscription for member if they don't have one
            from tafahom_api.apps.v1.billing.models import SubscriptionPlan
            free_plan = SubscriptionPlan.objects.get(plan_type='free')
            member_subscription = Subscription.objects.create(
                user=member,
                plan=free_plan,
                status="active"
            )

        # Deduct from Admin (bonus tokens first, then weekly allowance)
        remaining_to_deduct = amount
        if admin_subscription.bonus_tokens >= remaining_to_deduct:
            admin_subscription.bonus_tokens -= remaining_to_deduct
            remaining_to_deduct = 0
        else:
            remaining_to_deduct -= admin_subscription.bonus_tokens
            admin_subscription.bonus_tokens = 0

        if remaining_to_deduct > 0:
            admin_subscription.tokens_used += remaining_to_deduct

        admin_subscription.save(update_fields=["bonus_tokens", "tokens_used"])

        # Add to Member
        member_subscription.bonus_tokens += amount
        member_subscription.save(update_fields=["bonus_tokens"])

        # Transaction for Member
        TokenTransaction.objects.create(
            user=member,
            subscription=member_subscription,
            amount=amount,
            transaction_type="earned",
            reason=request.data.get("reason", f"Received from {request.user.organization_profile.organization_name}")
        )

        # Transaction for Admin (to track sharing)
        TokenTransaction.objects.create(
            user=request.user,
            subscription=admin_subscription,
            amount=-amount,
            transaction_type="used",
            reason=f"Shared with {member.username}"
        )

        return Response({
            "message": f"Successfully shared {amount} tokens with {member.username}",
            "member_bonus_tokens": member_subscription.bonus_tokens,
            "your_remaining_tokens": admin_subscription.remaining_tokens()
        })


class OrgRemoveTokensView(APIView):
    permission_classes = [IsOrganizationAdmin]

    def post(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, organization=request.user)
        except User.DoesNotExist:
            return Response({"detail": "Member not found"}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get("amount", 0)
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "Amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        member_subscription = getattr(member, 'subscription', None)
        if not member_subscription:
            return Response({"detail": "Member has no subscription"}, status=status.HTTP_400_BAD_REQUEST)

        # We can only take back what the member currently has in bonus tokens
        actual_removed = min(amount, member_subscription.bonus_tokens)
        if actual_removed <= 0:
             return Response({"detail": "Member has no bonus tokens to remove"}, status=status.HTTP_400_BAD_REQUEST)

        admin_subscription = getattr(request.user, 'subscription', None)
        if not admin_subscription:
             return Response({"detail": "You do not have an active subscription"}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct from Member
        member_subscription.bonus_tokens -= actual_removed
        member_subscription.save(update_fields=["bonus_tokens"])

        # Return to Admin (bonus tokens first, then reduce tokens_used)
        admin_subscription.bonus_tokens += actual_removed
        admin_subscription.save(update_fields=["bonus_tokens"])

        # Transaction for Member
        TokenTransaction.objects.create(
            user=member,
            subscription=member_subscription,
            amount=-actual_removed,
            transaction_type="used",
            reason=request.data.get("reason", f"Recovered by {request.user.organization_profile.organization_name}")
        )

        # Transaction for Admin
        TokenTransaction.objects.create(
            user=request.user,
            subscription=admin_subscription,
            amount=actual_removed,
            transaction_type="earned",
            reason=f"Recovered from {member.username}"
        )

        return Response({
            "message": f"Successfully removed {actual_removed} tokens from {member.username} and returned to your balance",
            "member_bonus_tokens": member_subscription.bonus_tokens,
            "your_remaining_tokens": admin_subscription.remaining_tokens()
        })


