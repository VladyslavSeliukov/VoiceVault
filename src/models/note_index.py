from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class NoteIndex(Base):
    """Tracks the synchronization state of Obsidian markdown files for vectorization."""

    __tablename__ = "notes_index"

    filepath: Mapped[str] = mapped_column(String, primary_key=True)

    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    last_indexed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    file_hash: Mapped[str] = mapped_column(String, nullable=True)
