from aiogram import Bot
from aiogram.types import BotCommand

from core.logger import logger


async def setup_bot_ui(bot: Bot) -> None:
    """Configures the Telegram Bot UI elements, such as the command menu."""
    commands = [
        BotCommand(command="tags", description="List all allowed taxonomy tags"),
        BotCommand(command="add_tag", description="Add a new tag to the allowed list"),
        BotCommand(command="del_tag", description="Remove a tag from the allowed list"),
        BotCommand(
            command="rag", description="Ask a question based on your Obsidian notes"
        ),
    ]

    await bot.set_my_commands(commands)
    logger.info("[telegram] Bot UI commands configured.")
