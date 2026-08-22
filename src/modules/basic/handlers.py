from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    """Handle the /start command and greet the user.

    Args:
        message: The incoming Telegram message object.
    """
    await message.answer("Welcome to VoiceVault!")


@router.message()
async def unhandled_message_fallback(message: Message) -> None:
    """Acts as a global fallback handler for unsupported messages or commands.

    Args:
        message (Message): The unhandled Telegram message object.
    """
    await message.answer("⚠️ Unknown command or text format")
