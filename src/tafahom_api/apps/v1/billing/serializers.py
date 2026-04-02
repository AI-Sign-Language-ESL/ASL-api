from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

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

    class Meta:
        model = Subscription
        fields = (
            "plan",
            "status",
            "billing_period",
            "end_date",
            "tokens_used",
            "bonus_tokens",
            "remaining_tokens",
            "is_active",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_remaining_tokens(self, obj):
        return obj.remaining_tokens()

    @extend_schema_field(serializers.BooleanField())
    def get_is_active(self, obj):
        return obj.status == "active"


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    billing_period = serializers.ChoiceField(choices=("monthly", "yearly"))


class UserTokensSerializer(serializers.Serializer):
    total_tokens = serializers.IntegerField()
    tokens_used = serializers.IntegerField()
    bonus_tokens = serializers.IntegerField()
    remaining_tokens = serializers.IntegerField()
    can_consume = serializers.BooleanField()
