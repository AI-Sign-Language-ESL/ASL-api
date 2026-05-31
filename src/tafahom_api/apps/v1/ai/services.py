import logging
from typing import List

from django.db import transaction
from django.utils.translation import get_language

from tafahom_api.apps.v1.billing.models import Subscription

from .fehm_data import (
    ACTIONS,
    INTENT_PATTERNS,
    PLAN_RANK,
    QA,
    WELCOME_AR,
    WELCOME_EN,
    WELCOME_QUICK_ACTIONS,
)
from .models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    @staticmethod
    def can_create_conversation(user) -> bool:
        from django.conf import settings
        count = Conversation.objects.filter(
            user=user, status="active"
        ).count()
        return count < settings.FEHM_MAX_CONVERSATIONS_PER_USER

    @staticmethod
    def create_conversation(user, title: str = "") -> Conversation:
        return Conversation.objects.create(user=user, title=title)

    @staticmethod
    def get_user_conversations(user):
        return Conversation.objects.filter(
            user=user, status="active"
        ).select_related("user")

    @staticmethod
    def archive_conversation(conversation: Conversation) -> Conversation:
        conversation.status = "archived"
        conversation.save(update_fields=["status"])
        return conversation

    @staticmethod
    def soft_delete_conversation(conversation: Conversation) -> Conversation:
        conversation.status = "deleted"
        conversation.save(update_fields=["status"])
        return conversation


class FehmResponseService:
    """Builds structured Fehm responses."""

    @staticmethod
    def welcome(user=None):
        lang = FehmResponseService._lang(user)
        message = WELCOME_AR if lang == "ar" else WELCOME_EN
        return {
            "type": "welcome",
            "message": message,
            "quick_actions": WELCOME_QUICK_ACTIONS,
        }

    @staticmethod
    def qa_answer(key: str, user=None):
        lang = FehmResponseService._lang(user)
        entry = QA.get(key)
        if not entry:
            return FehmResponseService.fallback(user)
        return {
            "type": "message",
            "message": entry.get(lang, entry.get("en", "")),
        }

    @staticmethod
    def action_response(action_key: str, user=None):
        action = ACTIONS.get(action_key)
        if not action:
            return FehmResponseService.fallback(user)
        resp = action["response"]
        lang = FehmResponseService._lang(user)
        return {
            "type": resp["type"],
            "message": resp.get(
                f"message_{lang}", resp.get("message_en", "")
            ),
            "destination": resp.get("destination"),
            "actions": resp.get("actions"),
        }

    @staticmethod
    def upgrade_required(action_key: str, user=None):
        action = ACTIONS.get(action_key, {})
        min_plan = action.get("min_plan", "enterprise")
        lang = FehmResponseService._lang(user)
        messages = {
            "en": f"This feature requires the {min_plan.title()} plan or higher. "
                  f"Please upgrade your subscription.",
            "ar": f"هذه الميزة تتطلب خطة {min_plan} أو أعلى. "
                  f"يرجى ترقية اشتراكك.",
        }
        return {
            "type": "upgrade_required",
            "message": messages.get(lang, messages["en"]),
            "required_plan": min_plan,
        }

    @staticmethod
    def fallback(user=None):
        lang = FehmResponseService._lang(user)
        messages = {
            "en": "I'm not sure I understand. Try asking 'What can you do?' or 'Help'.",
            "ar": "لست متأكداً أنني فهمت. حاول أن تسأل 'ماذا يمكنك أن تفعل؟' أو 'مساعدة'.",
        }
        return {
            "type": "message",
            "message": messages.get(lang, messages["en"]),
        }

    @staticmethod
    def _lang(user) -> str:
        if user and hasattr(user, "preferred_language") and user.preferred_language:
            return user.preferred_language
        lang = get_language()
        if lang and lang.startswith("ar"):
            return "ar"
        return "en"


class IntentRouter:
    """Matches user messages to intents or actions."""

    @staticmethod
    def resolve(message: str):
        text = message.lower().strip()

        # Try action patterns first
        for action_key, action in ACTIONS.items():
            for pattern in action["patterns"]:
                if pattern in text:
                    return {"type": "action", "key": action_key}

        # Try Q&A patterns
        for qa_key, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    return {"type": "qa", "key": qa_key}

        return {"type": "unknown"}


class ChatService:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation

    @transaction.atomic
    def add_user_message(self, content: str) -> Message:
        return Message.objects.create(
            conversation=self.conversation,
            role="user",
            content=content,
        )

    @transaction.atomic
    def add_assistant_message(self, content: str, extra: dict = None) -> Message:
        return Message.objects.create(
            conversation=self.conversation,
            role="assistant",
            content=content,
            extra_data=extra or {},
        )

    def process_message(self, content: str) -> dict:
        user = self.conversation.user
        self.add_user_message(content)

        intent = IntentRouter.resolve(content)

        if intent["type"] == "unknown":
            response = FehmResponseService.fallback(user)
            self.add_assistant_message(
                response["message"],
                extra={"type": response["type"]},
            )
            return response

        if intent["type"] == "qa":
            response = FehmResponseService.qa_answer(intent["key"], user)
            self.add_assistant_message(
                response["message"],
                extra={"type": response["type"], "key": intent["key"]},
            )
            return response

        if intent["type"] == "action":
            action = ACTIONS[intent["key"]]
            min_plan = action.get("min_plan")

            if min_plan:
                user_plan = self._get_user_plan(user)
                if PLAN_RANK.get(user_plan, 0) < PLAN_RANK.get(min_plan, 0):
                    response = FehmResponseService.upgrade_required(
                        intent["key"], user
                    )
                    self.add_assistant_message(
                        response["message"],
                        extra={"type": response["type"]},
                    )
                    return response

            response = FehmResponseService.action_response(intent["key"], user)
            self.add_assistant_message(
                response["message"],
                extra={"type": response["type"], "action": intent["key"]},
            )
            return response

        response = FehmResponseService.fallback(user)
        self.add_assistant_message(
            response["message"],
            extra={"type": response["type"]},
        )
        return response

    @staticmethod
    def _get_user_plan(user) -> str:
        try:
            return user.subscription.plan.plan_type
        except (Subscription.DoesNotExist, AttributeError):
            return "free"
