from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def build_flush_keyboard() -> ReplyKeyboardMarkup:
    """Builds a persistent reply keyboard for manual pipeline flushing.

    Creates a resized, persistent bottom keyboard with a single button
    that allows the user to manually trigger the transcription batching
    and LLM processing pipeline.

    Returns:
        ReplyKeyboardMarkup: The configured keyboard markup object containing the flush
            button.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📝 Flush & Process")]],
        resize_keyboard=True,
        is_persistent=True,
    )
