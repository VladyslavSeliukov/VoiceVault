import asyncio

from aiogram import Bot, Dispatcher

from core.broker import broker
from core.config import settings
from core.logger import logger
from core.middlewares import DbSessionMiddleware
from modules.basic.handlers import router as basic
from modules.telegram.handlers.rag import router as rag
from modules.telegram.handlers.tags import router as tags
from modules.telegram.handlers.voice import router as voice
from modules.telegram.ui import setup_bot_ui


async def on_startup(bot: Bot) -> None:
    """Execute tasks before the bot starts polling."""
    logger.info("[bot] Starting Telegram Bot...")
    await broker.startup()
    await setup_bot_ui(bot)


async def on_shutdown() -> None:
    """Execute tasks before the bot stops."""
    logger.info("[bot] Shutting down Telegram Bot...")
    await broker.shutdown()


async def main() -> None:
    """Initialize and start the Telegram bot application.

    This function configures the bot instance, initializes the dispatcher,
    includes all necessary routers, and starts long-polling.
    """
    bot = Bot(token=settings.BOT_TOKEN)
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
