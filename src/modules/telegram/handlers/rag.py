from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from core.exceptions import VoiceVaultError
from core.logger import logger
from modules.llm.client import generate_rag_response
from modules.obsidian.service import read_note_content
from modules.telegram.templates import UI
from modules.telegram.utils import md_to_telegram_html
from modules.vector.embeddings import generate_embedding
from modules.vector.qdrant import search_vectors

router = Router()


@router.message(Command("rag"))
async def handle_rag_command(message: Message, command: CommandObject) -> None:
    """Handles the /rag Telegram command to execute vector search and generate answers.

    Orchestrates the complete Retrieval-Augmented Generation (RAG) pipeline:
    validates the user input, generates an embedding for the query, retrieves
    the most relevant notes from Qdrant, reads their physical content, and
    invokes the LLM to generate an answer. Updates the Telegram UI dynamically
    to reflect the processing state.

    All internal exceptions (e.g., database timeouts, filesystem errors, or LLM
    failures) are caught and logged, notifying the user via the Telegram UI
    instead of raising an unhandled exception.

    Args:
        message (Message): The Telegram message object triggering the command.
        command (CommandObject): The parsed command arguments containing the user's
            actual query string.
    """
    if not command.args:
        await message.answer(UI.RAG_USAGE)
        return

    query = command.args

    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"[rag] Started RAG pipeline for user={user_id}")

    status_msg = await message.answer(UI.RAG_SEARCHING)

    try:
        query_vector = await generate_embedding(query)
        filepaths = await search_vectors(query_vector)

        if not filepaths:
            await status_msg.edit_text(UI.RAG_NO_NOTES)
            return

        context_parts: list[str] = []
        valid_sources: list[str] = []

        for filepath in filepaths:
            content = await read_note_content(filepath)
            if content:
                context_parts.append(f"--- Note: {filepath} ---\n{content}")
                valid_sources.append(filepath)

        if not context_parts:
            await status_msg.edit_text(UI.RAG_MISSING_FILES)
            return

        full_context = "\n\n".join(context_parts)

        await status_msg.edit_text(UI.RAG_ANALYZING)
        raw_answer = await generate_rag_response(query=query, context=full_context)
        safe_html_answer = md_to_telegram_html(raw_answer)

        sources_text = "\n".join([f"- <code>{src}</code>" for src in valid_sources])
        final_text = UI.RAG_ANSWER.format(answer=safe_html_answer, sources=sources_text)

        await status_msg.edit_text(final_text)

    except VoiceVaultError:
        logger.exception("[rag] Domain error processing RAG query")
        await status_msg.edit_text(UI.ERROR_INTERNAL)

    except Exception:
        logger.exception("[rag] Fatal unexpected error processing RAG query")
        await status_msg.edit_text(UI.ERROR_CRITICAL)
