import json
from channels.generic.websocket import AsyncWebsocketConsumer


class MeetingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # 🔐 Reject unauthenticated users
        if self.user.is_anonymous:
            await self.close()
            return

        self.meeting_code = self.scope["url_route"]["kwargs"]["code"]
        self.room_group_name = f"meeting_{self.meeting_code}"

        # Join room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # 🔥 Notify others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast",
                "message": {
                    "type": "user_joined",
                    "user": self.user.username
                }
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # 🔥 Notify others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast",
                "message": {
                    "type": "user_left",
                    "user": self.user.username
                }
            }
        )

    # =====================================================
    # RECEIVE (CORE LOGIC)
    # =====================================================
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handles:
        - WebRTC signaling
        - Chat
        - AI messages (future)
        """

        if text_data:
            data = json.loads(text_data)
            message_type = data.get("type")

            # ==========================================
            # 🎥 WebRTC SIGNALING
            # ==========================================
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

            # ==========================================
            # 💬 CHAT
            # ==========================================
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

            # ==========================================
            # 🤖 TEXT → SIGN (AI)
            # ==========================================
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

        # ==========================================
        # 🎤 AUDIO (Speech → Text)
        # ==========================================
        if bytes_data:
            import io
            from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient

            client = SpeechToTextClient()

            # Wrap the raw websocket bytes inside a BytesIO file-like object
            audio_buffer = io.BytesIO(bytes_data)

            # Direct await (since speech_to_text is already an async function)
            result = await client.speech_to_text(audio_buffer)

            text = result.get("text", "")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast",
                    "message": {
                        "type": "speech_result",
                        "text": text,
                        "user": self.user.username
                    }
                }
            )

    # =====================================================
    # SEND TO CLIENT
    # =====================================================
    async def broadcast(self, event):
        await self.send(text_data=json.dumps(event["message"]))