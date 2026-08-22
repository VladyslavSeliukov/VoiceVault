from pydantic import BaseModel, Field


class NoteAnalysis(BaseModel):
    """Schema for structuring raw voice transcripts into actionable Obsidian notes."""

    title: str = Field(
        ...,
        description="A short, concise title for the note (maximum 5-7 words). "
        "Suitable for a file name.",
    )
    summary: str = Field(
        ...,
        description="A clear, structured summary of the main points from the transcript"
        ". Use markdown formatting.",
    )
    action_points: list[str] = Field(
        default_factory=list,
        description="Actionable items or tasks extracted from the text. "
        "Empty list if no tasks are mentioned.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of context tags for Obsidian. "
        "CRITICAL: MUST be chosen exclusively from the allowed tags provided in the "
        "system instructions.It's okay not to choose anything. Do not creat new tags.",
    )
