import json
from typing import Any

from aiogram import Bot
from aiogram.types import ReplyKeyboardRemove

from core.logger import logger
from core.redis import redis_client
from modules.telegram.keyboards.voice import build_flush_keyboard
from modules.telegram.templates import UI


async def _handle_stt_completed(
    bot: Bot, user_id: int, status_id: int | None, payload: dict[str, Any]
) -> None:
    queue_length = payload.get("queue_length", 0)
    text = UI.STT_BUFFERED.format(queue_length=queue_length)

    if not status_id:
        await bot.send_message(
            chat_id=user_id, text=text, reply_markup=build_flush_keyboard()
        )
        return

    try:
        await bot.edit_message_text(chat_id=user_id, message_id=status_id, text=text)
    except Exception:
        await bot.delete_message(chat_id=user_id, message_id=status_id)
        await bot.send_message(
            chat_id=user_id, text=text, reply_markup=build_flush_keyboard()
        )


async def _handle_stt_error(
    bot: Bot, user_id: int, status_id: int | None, payload: dict[str, Any]
) -> None:
    error_type = payload.get("error_type")
    text = UI.ERROR_INTERNAL

    if error_type == "duplicate":
        text = UI.STT_DUPLICATE
    elif error_type == "empty":
        text = UI.STT_EMPTY
    elif error_type == "critical":
        text = UI.ERROR_CRITICAL

    if status_id:
        try:
            await bot.edit_message_text(
                chat_id=user_id, message_id=status_id, text=text
            )
        except Exception:
            pass


async def _handle_llm_completed(bot: Bot, user_id: int, status_id: int | None) -> None:
    if status_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=status_id)
        except Exception:
            pass

    await bot.send_message(
        chat_id=user_id, text=UI.LLM_SUCCESS, reply_markup=ReplyKeyboardRemove()
    )


async def _handle_llm_error(bot: Bot, user_id: int, status_id: int | None) -> None:
    if status_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=status_id)
        except Exception:
            pass

    await bot.send_message(chat_id=user_id, text=UI.ERROR_RETRY)


async def process_event(bot: Bot, payload: dict[str, Any]) -> None:
    """Routes a single parsed event to the appropriate handler."""
    event_type = payload.get("event_type")
    user_id = payload.get("user_id")
    status_id = payload.get("status_message_id")

    if not user_id or not event_type:
        return

    match event_type:
        case "stt_completed":
            await _handle_stt_completed(bot, user_id, status_id, payload)
        case "stt_error":
            await _handle_stt_error(bot, user_id, status_id, payload)
        case "llm_completed":
            await _handle_llm_completed(bot, user_id, status_id)
        case "llm_error":
            await _handle_llm_error(bot, user_id, status_id)
        case _:
            logger.warning(f"[listener] Unknown event type: {event_type}")


async def listen_ui_events(bot: Bot) -> None:
    """Background task to listen for UI events from Redis and update Telegram."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("telegram_ui_events")
    logger.info("[listener] Subscribed to telegram_ui_events channel")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                payload = json.loads(message["data"])
                await process_event(bot, payload)
            except Exception:
                logger.exception("[listener] Failed to process UI event")
    finally:
        await pubsub.unsubscribe("telegram_ui_events")
        await pubsub.close()
