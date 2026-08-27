class UI:
    """Centralized text templates for Telegram bot responses."""

    # Errors
    ERROR_INTERNAL = "❌ Could not process the request due to an internal system error."
    ERROR_CRITICAL = "❌ An unexpected critical error occurred."
    ERROR_RETRY = (
        "❌ Processing failed due to an error. We will try again automatically."
    )

    # RAG
    RAG_USAGE = "Please provide a question. Usage: /rag <your question>"
    RAG_SEARCHING = "🔍 Searching the knowledge base..."
    RAG_NO_NOTES = "🤷‍♂️ No relevant notes found in the database."
    RAG_MISSING_FILES = "❌ Found matching vectors, but the actual files are missing."
    RAG_ANALYZING = "🧠 Analyzing context and generating answer..."
    RAG_ANSWER = "🤖 <b>Answer:</b>\n{answer}\n\n📚 <b>Sources:</b>\n{sources}"

    # Tags
    TAGS_EMPTY = "No tags configured yet. Use /add_tag <name>."
    TAGS_LIST = "🏷 <b>Available tags:</b>\n{tags}"
    TAG_ADD_USAGE = "Please provide a tag name. Usage: /add_tag <name>"
    TAG_ADDED = "✅ Tag '{tag}' added successfully."
    TAG_EXISTS = "⚠️ Tag '{tag}' already exists."
    TAG_DEL_USAGE = "Please provide a tag name. Usage: /del_tag <name>"
    TAG_DELETED = "🗑️ Tag '{tag}' deleted successfully."
    TAG_NOT_FOUND = "⚠️ Tag '{tag}' not found."

    # Voice & Pipeline
    VOICE_DOWNLOAD_FAILED = "❌ Failed to download the voice message."
    VOICE_QUEUED = "⏳ Audio sent to STT queue. Waiting for Whisper..."
    VOICE_QUEUE_ERROR = "❌ Error: Could not send audio to processing queue."
    STT_DUPLICATE = "⚠️ Duplicate audio detected. Skipped."
    STT_EMPTY = "⚠️ Audio is empty or contains no speech."
    STT_BUFFERED = "✅ Transcribed and buffered. In queue: {queue_length} message(s)."
    FLUSH_START = "Processing your notes, please wait..."
    FLUSH_EMPTY = "❌ Buffer is empty."
    LLM_SUCCESS = "✅ Note processed and successfully saved to Obsidian!"
