from collections.abc import AsyncGenerator
from typing import Any

import pytest

from core.exceptions import BufferStateError
from core.redis import RedisKeys, redis_client
from modules.voice.buffer import (
    add_to_buffer,
    check_and_set_idempotency,
    get_and_clear_buffer,
    remove_idempotency_lock,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def user_id() -> AsyncGenerator[int, None]:
    """Provides a test user ID with automatic state cleanup.

    Yields:
        int: A mock Telegram user ID used for testing.
    """
    test_id: int = 100500
    yield test_id

    await redis_client.delete(
        RedisKeys.voice_buffer(test_id), RedisKeys.last_activity(test_id)
    )


@pytest.fixture
async def lock_key() -> AsyncGenerator[str, None]:
    """Provides a Redis idempotency lock key with automatic teardown.

    Yields:
        str: The fully qualified Redis key string for the idempotency lock.
    """
    key: str = RedisKeys.stt_idempotency("test_fixture_file")
    yield key
    await redis_client.delete(key)


class TestIdempotency:
    """Tests for Redis-based idempotency locks to prevent duplicate processing."""

    async def test_lock_behavior(self, lock_key: str) -> None:
        """Verifies that consecutive locking attempts are rejected."""
        is_new: bool = await check_and_set_idempotency(lock_key)
        assert is_new is True

        is_new_again: bool = await check_and_set_idempotency(lock_key)
        assert is_new_again is False

    async def test_lock_removal(self, lock_key: str) -> None:
        """Verifies that an operation is allowed again after removing the lock."""
        await check_and_set_idempotency(lock_key)
        await remove_idempotency_lock(lock_key)

        is_new: bool = await check_and_set_idempotency(lock_key)
        assert is_new is True


class TestBufferOperations:
    """Tests for managing the user transcript buffer and Redis pipeline transactions."""

    async def test_add_to_buffer(self, user_id: int) -> None:
        """Verifies the buffer size increments correctly on consecutive additions."""
        size: int = await add_to_buffer(user_id, "First message")
        assert size == 1

        size_second: int = await add_to_buffer(user_id, "Second message")
        assert size_second == 2

    async def test_get_and_clear_buffer(self, user_id: int) -> None:
        """Verifies reading returns all items and completely flushes the queue."""
        await add_to_buffer(user_id, "Hello")
        await add_to_buffer(user_id, "World")

        items: list[dict[str, Any]] = await get_and_clear_buffer(user_id)

        assert len(items) == 2
        assert items[0]["transcript"] == "Hello"
        assert items[1]["transcript"] == "World"

        empty_items: list[dict[str, Any]] = await get_and_clear_buffer(user_id)
        assert len(empty_items) == 0

    async def test_buffer_unicode_support(self, user_id: int) -> None:
        """Verifies safe handling of unicode characters and emojis in Redis."""
        text_with_special_chars: str = (
            "✅ Note processed and successfully saved to Obsidian!"
        )

        await add_to_buffer(user_id, text_with_special_chars)
        items: list[dict[str, Any]] = await get_and_clear_buffer(user_id)

        assert len(items) == 1
        assert items[0]["transcript"] == text_with_special_chars

    async def test_buffer_corrupted_json(self, user_id: int) -> None:
        """Verifies BufferStateError is raised when reading malformed JSON data."""
        buffer_key: str = RedisKeys.voice_buffer(user_id)
        await redis_client.rpush(buffer_key, "invalid_json_}{")

        with pytest.raises(BufferStateError, match="Failed to get and clear buffer"):
            await get_and_clear_buffer(user_id)


class TestErrorHandling:
    """Tests for network failures, timeouts, and unexpected Redis connection drops."""

    async def test_redis_connection_error_handling(
        self, lock_key: str, mocker: Any
    ) -> None:
        """Verifies connection loss during idempotency check raises BufferStateError."""
        mocker.patch(
            "modules.voice.buffer.redis_client.set",
            side_effect=Exception("Redis connection lost"),
        )

        with pytest.raises(BufferStateError, match="Idempotency check failed"):
            await check_and_set_idempotency(lock_key)

    async def test_add_to_buffer_error(self, user_id: int, mocker: Any) -> None:
        """Verify transaction failure in buffer addition raises BufferStateError."""
        mocker.patch(
            "modules.voice.buffer.redis_client.pipeline",
            side_effect=Exception("Redis pipeline failed"),
        )

        with pytest.raises(
            BufferStateError,
            match=f"Failed to add transcript to buffer for user {user_id}",
        ):
            await add_to_buffer(user_id, "Test transcript")

    async def test_remove_idempotency_lock_error(
        self, lock_key: str, mocker: Any
    ) -> None:
        """Verifies failure during lock key deletion raises BufferStateError."""
        mocker.patch(
            "modules.voice.buffer.redis_client.delete",
            side_effect=Exception("Redis delete failed"),
        )

        with pytest.raises(
            BufferStateError, match=f"Idempotency lock removal failed for '{lock_key}'"
        ):
            await remove_idempotency_lock(lock_key)
