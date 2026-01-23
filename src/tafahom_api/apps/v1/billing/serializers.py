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
            "credits_per_month",
            "price",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    remaining_credits = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            "plan",
            "status",
            "billing_period",
            "end_date",
            "credits_used",
            "bonus_credits",
            "remaining_credits",
            "is_active",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_remaining_credits(self, obj):
        return obj.remaining_credits()

    @extend_schema_field(serializers.BooleanField())
    def get_is_active(self, obj):
        return obj.status == "active"


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    billing_period = serializers.ChoiceField(choices=("monthly", "yearly"))


class UserCreditsSerializer(serializers.Serializer):
    total_credits = serializers.IntegerField()
    credits_used = serializers.IntegerField()
    bonus_credits = serializers.IntegerField()
    remaining_credits = serializers.IntegerField()
    can_consume = serializers.BooleanField()
