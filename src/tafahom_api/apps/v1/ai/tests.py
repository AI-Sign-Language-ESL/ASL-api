from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan

from .models import Conversation, Message

User = get_user_model()


class WelcomeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_welcome_unauthenticated(self):
        response = self.client.get("/api/v1/ai/welcome/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "welcome")
        self.assertIn("Fehm", response.data["message"])
        self.assertIn("quick_actions", response.data)

    def test_welcome_authenticated(self):
        user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/ai/welcome/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ConversationAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = "/api/v1/ai/conversations/"

    def test_create_conversation(self):
        response = self.client.post(self.list_url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_list_conversations(self):
        Conversation.objects.create(user=self.user, title="Chat 1")
        Conversation.objects.create(user=self.user, title="Chat 2")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_archive_conversation(self):
        conv = Conversation.objects.create(user=self.user, title="Archivable")
        url = f"/api/v1/ai/conversations/{conv.id}/archive/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        conv.refresh_from_db()
        self.assertEqual(conv.status, "archived")

    def test_delete_conversation(self):
        conv = Conversation.objects.create(user=self.user, title="Deletable")
        url = f"/api/v1/ai/conversations/{conv.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        conv.refresh_from_db()
        self.assertEqual(conv.status, "deleted")

    def test_other_user_cannot_access(self):
        other = User.objects.create_user(
            username="other", password="testpass123"
        )
        conv = Conversation.objects.create(user=other, title="Private")
        url = f"/api/v1/ai/conversations/{conv.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ChatAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="free",
            defaults={"name": "Free Plan", "weekly_tokens_limit": 50, "price": 0},
        )
        Subscription.objects.get_or_create(
            user=self.user, defaults={"plan": plan, "status": "active"}
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.conversation = Conversation.objects.create(
            user=self.user, title="Chat"
        )

    def test_send_message_receives_reply(self):
        url = f"/api/v1/ai/conversations/{self.conversation.id}/messages/send/"
        response = self.client.post(url, {"content": "what is tafahom"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("type", response.data)
        # Message should be saved
        self.assertEqual(Message.objects.count(), 2)  # user + assistant

    def test_send_unknown_message(self):
        url = f"/api/v1/ai/conversations/{self.conversation.id}/messages/send/"
        response = self.client.post(
            url, {"content": "xyznonsense123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("not sure", response.data["message"].lower())

    def test_list_messages(self):
        Message.objects.create(
            conversation=self.conversation, role="user", content="Hello"
        )
        Message.objects.create(
            conversation=self.conversation, role="assistant", content="Hi there"
        )
        url = f"/api/v1/ai/conversations/{self.conversation.id}/messages/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)


class PlanGatedActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="freeuser", password="testpass123"
        )
        plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="free",
            defaults={"name": "Free Plan", "weekly_tokens_limit": 50, "price": 0},
        )
        Subscription.objects.get_or_create(
            user=self.user, defaults={"plan": plan, "status": "active"}
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.conversation = Conversation.objects.create(
            user=self.user, title="Chat"
        )

    def test_create_meeting_blocked_for_free(self):
        url = f"/api/v1/ai/conversations/{self.conversation.id}/messages/send/"
        response = self.client.post(
            url, {"content": "create meeting"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "upgrade_required")


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_conversation_str(self):
        conv = Conversation.objects.create(
            user=self.user, title="My Chat"
        )
        self.assertIn("My Chat", str(conv))

    def test_message_str(self):
        conv = Conversation.objects.create(user=self.user)
        msg = Message.objects.create(
            conversation=conv, role="user", content="Hello world"
        )
        self.assertIn("Hello world", str(msg))

    def test_default_status_is_active(self):
        conv = Conversation.objects.create(user=self.user)
        self.assertEqual(conv.status, "active")
