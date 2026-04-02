import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan, TokenTransaction
from django.db import transaction

class MeetingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for meetings.
    Enforces 'GO' plan and consumes 50 tokens upon a successful connection.
    """

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)  # Unauthorized
            return

        # Check plan and tokens
        allowed, message = await self._check_access()
        if not allowed:
            await self.accept() # Accept to send the error message before closing
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": message
            }))
            await self.close(code=4003) # Forbidden
            return

        # Success - Consume tokens
        consumed = await self._consume_tokens()
        if not consumed:
             await self.accept()
             await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Token deduction failed."
            }))
             await self.close(code=4003)
             return

        self.room_name = self.scope['url_route']['kwargs'].get('room_name', 'default')
        self.room_group_name = f'meeting_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": f"Welcome to meeting room: {self.room_name}. 50 tokens deducted.",
            "user": self.user.username
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'meeting_message',
                'message': message,
                'sender': self.user.username
            }
        )

    async def meeting_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender']
        }))

    @database_sync_to_async
    def _check_access(self):
        try:
            subscription = self.user.subscription
        except ObjectDoesNotExist:
            return False, "No active subscription found. Upgrade to GO."

        # Plan Check
        plan_rank = {"free": 0, "basic": 1, "go": 2, "premium": 3}
        if plan_rank.get(subscription.plan.plan_type, 0) < 2: # GO plan is rank 2
            return False, "Meetings require a GO or PREMIUM plan."

        # Token Check
        if not subscription.can_consume(50):
            return False, f"Not enough tokens. Meeting requires 50 tokens. Current: {subscription.remaining_tokens()}"

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
