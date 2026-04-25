import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from tafahom_api.apps.v1.billing.models import Subscription, TokenTransaction


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

        # Consume tokens
        consumed = await self._consume_tokens()
        if not consumed:
            await self.accept()
            await self.send(text_data=json.dumps({"type": "error", "message": "Token deduction failed."}))
            await self.close(code=4003)
            return

        self.meeting_code = self.scope["url_route"]["kwargs"]["code"]
        self.room_group_name = f"meeting_{self.meeting_code}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": f"Welcome to meeting {self.meeting_code}. 50 tokens deducted.",
            "user": self.user.username
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type in ["offer", "answer", "ice_candidate"]:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "broadcast", "message": {"type": message_type, "data": data.get("data"), "user": self.user.username}}
                )
            elif message_type == "chat":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "broadcast", "message": {"type": "chat", "message": data.get("message"), "user": self.user.username}}
                )
            elif message_type == "text_to_sign":
                from tafahom_api.apps.v1.translation.services.streaming_translation_service import TranslationPipelineService
                result = await TranslationPipelineService.text_to_sign(data.get("text"))
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "broadcast", "message": {"type": "sign_result", "gloss": result.get("gloss"), "user": self.user.username}}
                )

        if bytes_data:
            import io
            from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
            client = SpeechToTextClient()
            result = await client.speech_to_text(io.BytesIO(bytes_data))
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "broadcast", "message": {"type": "speech_result", "text": result.get("text", ""), "user": self.user.username}}
            )

    async def broadcast(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def _check_access(self):
        try:
            subscription = self.user.subscription
        except ObjectDoesNotExist:
            return False, "No subscription. Upgrade to GO."

        plan_rank = {"free": 0, "basic": 1, "go": 2, "premium": 3}
        if plan_rank.get(subscription.plan.plan_type, 0) < 2:
            return False, "Meetings require GO or PREMIUM plan."

        if not subscription.can_consume(50):
            return False, f"Not enough tokens. Need 50, have {subscription.remaining_tokens()}"

        return True, ""

    @database_sync_to_async
    def _consume_tokens(self):
        try:
            with transaction.atomic():
                subscription = Subscription.objects.select_for_update().get(user=self.user)
                if subscription.can_consume(50):
                    subscription.consume(50)
                    TokenTransaction.objects.create(
                        user=self.user,
                        subscription=subscription,
                        amount=-50,
                        transaction_type="used",
                        reason="Meeting WebSocket Join"
                    )
                    return True
                return False
        except Exception:
            return False