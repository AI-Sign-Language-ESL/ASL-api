from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import DatasetContribution
from tafahom_api.apps.v1.billing.services import reward_dataset_contribution

@admin.register(DatasetContribution)
class DatasetContributionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_target_word",
        "video_preview",
        "contributor_email", # ✅ Changed from 'user' to custom helper
        "status",
        "created_at",
    )

    # ✅ FIX: Search using 'word' and 'contributor' (not gloss/user)
    search_fields = ("word", "contributor__email", "contributor__username")
    
    list_filter = ("status", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "reviewed_at", "video_preview")

    actions = ["approve_selected", "reject_selected"]

    # --------------------------------------------------
    # CUSTOM COLUMNS
    # --------------------------------------------------
    # ✅ FIX: Ordering by 'word'
    @admin.display(ordering='word', description='Target Word')
    def get_target_word(self, obj):
        return format_html(
            '<span style="font-size: 16px; font-weight: bold; color: #2c3e50;">{}</span>', 
            obj.word.upper() # ✅ FIX: obj.word
        )

    @admin.display(description='Contributor', ordering='contributor')
    def contributor_email(self, obj):
        return obj.contributor.email

    def video_preview(self, obj):
        # ✅ FIX: obj.video instead of obj.file
        if obj.video: 
            return format_html(
                '''
                <video width="200" height="150" controls style="border-radius: 8px; border: 1px solid #ddd;">
                    <source src="{}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                ''',
                obj.video.url
            )
        return "No Video"
    
    video_preview.short_description = "Sign Video"

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------
    @admin.action(description="✅ Approve selected & Reward User")
    def approve_selected(self, request, queryset):
        success_count = 0
        
        for contribution in queryset.filter(status="pending"):
            try:
                # 1. Approve Logic
                contribution.approve(request.user)
                
                # 2. Reward Logic
                # ✅ FIX: Access 'contributor' instead of 'user'
                if hasattr(contribution.contributor, 'subscription'):
                    reward_dataset_contribution(
                        subscription=contribution.contributor.subscription,
                        credits=10
                    )
                success_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error processing ID {contribution.id}: {e}", 
                    level=messages.WARNING
                )

        if success_count > 0:
            self.message_user(request, f"Successfully approved {success_count} contributions.")

    @admin.action(description="❌ Reject selected")
    def reject_selected(self, request, queryset):
        count = 0
        for contribution in queryset.filter(status="pending"):
            # This handles the state transition safely
            contribution.reject(request.user)
            count += 1
        self.message_user(request, f"Rejected {count} contributions.")