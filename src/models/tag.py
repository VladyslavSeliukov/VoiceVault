from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """SQLAlchemy model representing an allowed taxonomy tag."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)

    def __repr__(self) -> str:
        """Provide a developer-friendly string representation of the Tag.

        Returns:
            str: A string in the format '<Tag {name}>' for easier debugging
                and logging.
        """
        return f"<Tag {self.name}>"
