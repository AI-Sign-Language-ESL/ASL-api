from django.contrib import admin
from .models import SubscriptionPlan, Subscription, TokenTransaction

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'weekly_tokens_limit', 'price', 'is_active')
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('price',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'billing_period', 'tokens_used', 'bonus_tokens', 'get_remaining_tokens', 'last_reset', 'end_date')
    list_filter = ('status', 'billing_period', 'plan')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_reset',)

    def get_remaining_tokens(self, obj):
        return obj.remaining_tokens()
    get_remaining_tokens.short_description = 'Remaining Tokens'

@admin.register(TokenTransaction)
class TokenTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'transaction_type', 'reason', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
