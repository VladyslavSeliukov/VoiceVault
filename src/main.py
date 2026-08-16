import asyncio

from aiogram import Bot, Dispatcher

from core.config import settings
from modules.basic.handlers import router as basic
from modules.telegram.handlers.voice import router as voice


async def main() -> None:
    """Initialize and start the Telegram bot application.

    This function configures the bot instance, initializes the dispatcher,
    includes all necessary routers, and starts long-polling.
    """
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(basic)
    dp.include_router(voice)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
