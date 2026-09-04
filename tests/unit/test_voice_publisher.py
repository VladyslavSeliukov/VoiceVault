from typing import Any

import pytest

from modules.voice.publisher import publish_ui_event

pytestmark = pytest.mark.asyncio


class TestUIEventPublisher:
    """Test publishing async UI update events to Redis Pub/Sub channel."""

    async def test_publish_ui_event_success(self, mocker: Any) -> None:
        """Verifies successful serialization and publication of a UI event to Redis."""
        mock_event: Any = mocker.Mock()
        mock_event.model_dump_json.return_value = '{"test": "data"}'
        mock_event.event_type = "test_event"
        mock_event.user_id = 123

        mock_publish: Any = mocker.patch(
            "modules.voice.publisher.redis_client.publish",
            new_callable=mocker.AsyncMock,
        )

        await publish_ui_event(mock_event)

        mock_publish.assert_called_once_with("telegram_ui_events", '{"test": "data"}')

    async def test_publish_ui_event_error(self, mocker: Any) -> None:
        """Verify network errors during publish are ignored to prevent crash."""
        mock_event: Any = mocker.Mock()
        mock_event.model_dump_json.return_value = '{"test": "data"}'
        mock_event.event_type = "test_error_event"
        mock_event.user_id = 456

        mock_publish: Any = mocker.patch(
            "modules.voice.publisher.redis_client.publish",
            side_effect=Exception("Redis connection lost"),
        )

        await publish_ui_event(mock_event)

        mock_publish.assert_called_once()
