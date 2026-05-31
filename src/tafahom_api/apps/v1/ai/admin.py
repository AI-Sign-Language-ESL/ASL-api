from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    fields = ("role", "content", "tokens_used", "model_used", "created_at")
    readonly_fields = fields
    ordering = ("created_at",)
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username", "user__email")
    inlines = [MessageInline]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "tokens_used", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("conversation__title", "content")
    readonly_fields = ("id", "created_at")
