import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Meeting, Participant

User = get_user_model()


class MeetingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket for meetings.
    - Requires GO plan
    - Consumes 50 tokens on join
    - Supports WebRTC, chat, text-to-sign, speech-to-text
    """

    async def connect(self):
        self.user = self.scope["user"]

        # Reject unauthenticated
        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        # Check plan and tokens
        allowed, message = await self._check_access()
        if not allowed:
            await self.accept()
            await self.send(text_data=json.dumps({"type": "error", "message": message}))
            await self.close(code=4003)
            return

        # Consume tokens (10 tokens per meeting)
        consumed = await self._consume_tokens()
        if not consumed:
            await self.close(code=4003)
            return

        # Join meeting room group
        self.meeting_code = self.scope["url_route"]["kwargs"]["code"]
        self.room_group_name = f"meeting_{self.meeting_code}"

        # Verify meeting exists and is active
        meeting = await self._get_meeting(self.meeting_code)
        if not meeting or not meeting.is_active:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast",
                "message": {
                    "type": "user_joined",
                    "user": self.user.username,
                    "role": await self._get_user_role(self.user, meeting),
                }
            }
        )

        # Send confirmation to user
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": f"Welcome to meeting {self.meeting_code}. 10 tokens deducted.",
            "user": self.user.username
        }))

    async def disconnect(self, close_code):
        # Notify others that user left
        if hasattr(self, 'room_group_name') and hasattr(self, 'user'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast",
                    "message": {
                        "type": "user_left",
                        "user": self.user.username,
                    }
                }
            )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
            message_type = data.get("type")

            # === WEBRTC SIGNALING ===
            if message_type in ["offer", "answer", "ice_candidate"]:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "broadcast",
                        "message": {
                            "type": message_type,
                            "data": data.get("data"),
                            "user": self.user.username
                        }
                    }
                )

            # === CHAT MESSAGES ===
            elif message_type == "chat":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "broadcast",
                        "message": {
                            "type": "chat",
                            "message": data.get("message"),
                            "user": self.user.username
                        }
                    }
                )

            # === TEXT TO SIGN TRANSLATION ===
            elif message_type == "text_to_sign":
                from tafahom_api.apps.v1.translation.services.streaming_translation_service import TranslationPipelineService
                result = await TranslationPipelineService.text_to_sign(data.get("text"))
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "broadcast",
                        "message": {
                            "type": "sign_result",
                            "gloss": result.get("gloss"),
                            "user": self.user.username
                        }
                    }
                )

        # === SPEECH TO TEXT (BINARY AUDIO DATA) ===
        if bytes_data:
            from io import BytesIO
            from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
            client = SpeechToTextClient()
            result = await client.speech_to_text(BytesIO(bytes_data))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast",
                    "message": {
                        "type": "speech_result",
                        "text": result.get("text", ""),
                        "user": self.user.username
                    }
                }
            )

    async def broadcast(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def _check_access(self):
        """Check if user has sufficient tokens"""
        from tafahom_api.apps.v1.billing.models import Subscription
        try:
            subscription = Subscription.objects.get(user=self.user)
            if subscription.remaining_tokens() < 10:
                return False, "Insufficient tokens. Need 10 tokens to join meeting."
            return True, None
        except Subscription.DoesNotExist:
            return False, "Subscription not found"

    @database_sync_to_async
    def _consume_tokens(self):
        """Deduct 10 tokens for meeting"""
        from tafahom_api.apps.v1.billing.models import Subscription
        from tafahom_api.apps.v1.billing.services import consume_meeting_token
        try:
            subscription = Subscription.objects.get(user=self.user)
            return consume_meeting_token(subscription, amount=10)
        except Exception:
            return False

    @database_sync_to_async
    def _get_meeting(self, code):
        return Meeting.objects.filter(meeting_code=code, is_active=True).first()

    @database_sync_to_async
    def _get_user_role(self, user, meeting):
        try:
            participant = Participant.objects.get(user=user, meeting=meeting)
            return participant.role
        except Participant.DoesNotExist:
            return "participant"
