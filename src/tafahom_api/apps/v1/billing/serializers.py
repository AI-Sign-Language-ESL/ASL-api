from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from datetime import timedelta

from .models import Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "plan_type",
            "weekly_tokens_limit",
            "price",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    remaining_tokens = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    next_reset = serializers.SerializerMethodField()
    total_tokens = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            "plan",
            "status",
            "billing_period",
            "end_date",
            "start_date",
            "last_reset",
            "next_reset",
            "tokens_used",
            "bonus_tokens",
            "total_tokens",
            "remaining_tokens",
            "is_active",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_remaining_tokens(self, obj):
        return obj.remaining_tokens()

    @extend_schema_field(serializers.IntegerField())
    def get_total_tokens(self, obj):
        return obj.total_tokens()

    @extend_schema_field(serializers.BooleanField())
    def get_is_active(self, obj):
        return obj.status == "active"

    @extend_schema_field(serializers.DateTimeField())
    def get_next_reset(self, obj):
        return obj.last_reset + timedelta(days=7)


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    billing_period = serializers.ChoiceField(choices=("monthly", "yearly"))


class UserTokensSerializer(serializers.Serializer):
    total_tokens = serializers.IntegerField()
    tokens_used = serializers.IntegerField()
    bonus_tokens = serializers.IntegerField()
    remaining_tokens = serializers.IntegerField()
    can_consume = serializers.BooleanField()
