from pydantic import BaseModel


class UIEventBase(BaseModel):
    """Base schema for all UI events pushed by background workers."""

    event_type: str
    user_id: int
    status_message_id: int | None = None


class STTCompletedEvent(UIEventBase):
    """Event emitted when the Speech-to-Text phase successfully finishes."""

    event_type: str = "stt_completed"
    queue_length: int


class STTErrorEvent(UIEventBase):
    """Event emitted when an error occurs during the Speech-to-Text phase."""

    event_type: str = "stt_error"
    error_type: str


class LLMCompletedEvent(UIEventBase):
    """Event emitted when the LLM analysis finishes and the note is saved."""

    event_type: str = "llm_completed"


class LLMErrorEvent(UIEventBase):
    """Event emitted when an error occurs during the LLM analysis phase."""

    event_type: str = "llm_error"
