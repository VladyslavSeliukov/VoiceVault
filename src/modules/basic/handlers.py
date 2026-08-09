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
