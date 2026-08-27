class VoiceVaultError(Exception):
    """Base exception for all domain errors in VoiceVault."""

    pass


class VectorStorageError(VoiceVaultError):
    """Base exception for Qdrant and embedding operations."""

    pass


class LLMProcessingError(VoiceVaultError):
    """Raised when the local LLM fails to analyze the transcript."""

    pass


class STTProcessingError(VoiceVaultError):
    """Raised when whisper.cpp fails to transcribe the audio."""

    pass


class VaultIOError(VoiceVaultError):
    """Raised when failing to read or write markdown files to Obsidian."""

    pass


class BufferStateError(VoiceVaultError):
    """Raised when Redis operations for user buffering fail."""

    pass


class DatabaseError(VoiceVaultError):
    """Raised when a database transaction or connection fails."""

    pass


class PipelineError(VoiceVaultError):
    """Raised when the background pipeline orchestration or message broker fails."""

    pass
