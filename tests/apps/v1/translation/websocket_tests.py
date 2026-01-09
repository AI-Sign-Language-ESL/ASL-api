import pytest
import json
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from unittest.mock import patch, AsyncMock

# Adjust this import to match your project's ASGI application path
from tafahom_api.asgi import application

User = get_user_model()


@pytest.mark.asyncio
@pytest.mark.django_db
class TestTranslationWebSocketAuth:
    async def test_rejects_anonymous(self):
        communicator = WebsocketCommunicator(application, "/ws/translation/stream/")
        connected, _ = await communicator.connect()
        assert not connected
        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
class TestTranslationWebSocketFlow:
    async def test_authenticated_connection(self, jwt_user_token):
        # We Mock the service here too, just in case connect() calls .start()
        with patch(
            "tafahom_api.apps.v1.translation.consumers.StreamingTranslationService"
        ) as MockService:
            # Configure the mock to be awaitable
            mock_instance = MockService.return_value
            mock_instance.start = AsyncMock(return_value=None)
            mock_instance.shutdown = AsyncMock(return_value=None)

            communicator = WebsocketCommunicator(
                application, f"/ws/translation/stream/?token={jwt_user_token}"
            )

            connected, _ = await communicator.connect()
            assert connected
            await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
class TestTranslationWebSocketStreaming:
    async def test_start_and_stop_translation(self, jwt_user_token):
        # 🛡️ KEY FIX: Mock the Service so it doesn't crash the test
        with patch(
            "tafahom_api.apps.v1.translation.consumers.StreamingTranslationService"
        ) as MockService:
            # Setup the Mock instance
            mock_service_instance = MockService.return_value

            # Make the methods AsyncMocks so they can be 'awaited'
            mock_service_instance.start = AsyncMock(return_value=None)
            mock_service_instance.start_translation = AsyncMock(return_value=None)
            mock_service_instance.stop_translation = AsyncMock(return_value=None)
            mock_service_instance.shutdown = AsyncMock(return_value=None)

            # Initialize Communicator
            communicator = WebsocketCommunicator(
                application, f"/ws/translation/stream/?token={jwt_user_token}"
            )

            # 1. Connect
            connected, _ = await communicator.connect()
            assert connected

            # 2. Send Start Action
            await communicator.send_json_to({"action": "start", "output_type": "text"})

            # 3. Receive "Processing" Status
            response = await communicator.receive_json_from()
            assert response["type"] == "status"
            assert response["status"] == "processing"

            # 4. Send Stop Action
            await communicator.send_json_to({"action": "stop"})

            # 5. Receive "Stopped" Status
            response = await communicator.receive_json_from()

            # 🛡️ Debugging help: print response if it fails
            if "status" not in response:
                pytest.fail(f"Expected status message, got: {response}")

            assert response["status"] == "stopped"

            await communicator.disconnect()
