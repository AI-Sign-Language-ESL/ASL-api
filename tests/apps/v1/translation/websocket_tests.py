import pytest
from channels.testing import WebsocketCommunicator

from tafahom_api.asgi import application


@pytest.mark.asyncio
@pytest.mark.django_db
class TestTranslationWebSocketAuth:
    async def test_rejects_anonymous(self):
        communicator = WebsocketCommunicator(
            application,
            "/ws/translation/stream/",
        )

        connected, _ = await communicator.connect()
        assert connected is False


@pytest.mark.asyncio
@pytest.mark.django_db
class TestTranslationWebSocketFlow:
    async def test_authenticated_connection(
        self,
        existing_user,
        jwt_user_token: str,
    ):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/translation/stream/?token={jwt_user_token}",
        )

        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
class TestTranslationWebSocketStreaming:
    async def test_start_and_stop_translation(
        self,
        jwt_user_token: str,
    ):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/translation/stream/?token={jwt_user_token}",
        )

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"action": "start", "output_type": "text"})

        response = await communicator.receive_json_from()
        assert response["type"] == "status"
        assert response["status"] == "processing"

        await communicator.send_json_to({"action": "stop"})
        response = await communicator.receive_json_from()
        assert response["status"] == "stopped"

        await communicator.disconnect()
