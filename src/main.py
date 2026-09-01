import asyncio
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.broker import broker
from core.config import settings
from core.logger import logger
from core.metrics.server import start_metrics_server
from modules.telegram.handlers.basic import router as basic
from modules.telegram.handlers.rag import router as rag
from modules.telegram.handlers.tags import router as tags
from modules.telegram.handlers.voice import router as voice
from modules.telegram.listener import listen_ui_events
from modules.telegram.middlewares import DbSessionMiddleware
from modules.telegram.ui import setup_bot_ui


async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    """Execute tasks before the bot starts polling."""
    logger.info("[bot] Starting Telegram Bot...")

    start_metrics_server(settings.METRICS_PORT_BOT, "bot")

    await broker.startup()
    await setup_bot_ui(bot)

    dispatcher["listener_task"] = asyncio.create_task(listen_ui_events(bot))


async def on_shutdown(dispatcher: Dispatcher) -> None:
    """Execute tasks before the bot stops."""
    logger.info("[bot] Shutting down Telegram Bot...")

    listener_task: asyncio.Task[Any] | None = dispatcher.get("listener_task")
    if listener_task:
        listener_task.cancel()

    await broker.shutdown()


async def main() -> None:
    """Initialize and start the Telegram bot application.

    This function configures the bot instance, initializes the dispatcher,
    includes all necessary routers, and starts long-polling.
    """
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(basic)
    dp.include_router(voice)
    dp.include_router(tags)
    dp.include_router(rag)

    logger.info("[bot] Configuration loaded. Starting polling...")
    try:
        await dp.start_polling(bot)
    except Exception:
        logger.exception("[bot] Fatal error occurred during bot polling.")
        raise
    finally:
        logger.info("[bot] Application stopped.")


if __name__ == "__main__":
    asyncio.run(main())
