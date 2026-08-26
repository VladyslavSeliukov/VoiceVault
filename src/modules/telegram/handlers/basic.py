from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from core.logger import logger

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    """Handle the /start command and greet the user.

    Args:
        message: The incoming Telegram message object.
    """
    user_id = message.from_user.id if message.from_user else "unknown"
    user_name = message.from_user.full_name if message.from_user else "Unknown User"

    logger.info(f"[basic] User started the bot: {user_name} (ID: {user_id})")

    try:
        await message.answer("Welcome to VoiceVault!")
    except Exception:
        logger.exception(f"[basic] Failed to send welcome message to user {user_id}")
