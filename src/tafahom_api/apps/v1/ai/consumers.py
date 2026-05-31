import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation
from .services import ChatService, FehmResponseService

logger = logging.getLogger(__name__)


class FehmChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        self.conversation = await self._get_conversation()

        if not self.conversation:
            await self.close(code=4004)
            return

        if self.conversation.status != "active":
            await self.close(code=4003)
            return

        await self.accept()
        self.chat_service = ChatService(self.conversation)

        await self.send(text_data=json.dumps({
            "type": "connected",
            "conversation_id": str(self.conversation.id),
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error", "detail": "Invalid JSON",
            }))
            return

        msg_type = data.get("type", "message")

        if msg_type == "welcome":
            response = FehmResponseService.welcome(self.user)
            await self.send(text_data=json.dumps(response))

        elif msg_type == "message":
            content = data.get("content", "").strip()
            if not content:
                await self.send(text_data=json.dumps({
                    "type": "error", "detail": "Content cannot be empty",
                }))
                return

            response = await self._process_message(content)
            await self.send(text_data=json.dumps(response))

        elif msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    @database_sync_to_async
    def _get_conversation(self):
        try:
            return Conversation.objects.get(
                id=self.conversation_id, user=self.user
            )
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def _process_message(self, content: str) -> dict:
        return self.chat_service.process_message(content)
