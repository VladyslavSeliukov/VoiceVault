from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from core.logger import logger
from models.tag import Tag


def _normalize_tag(name: str) -> str:
    """Normalizes a tag name according to domain business rules.

    Args:
        name (str): The raw tag name to be normalized.

    Returns:
        str: The normalized tag name (lowercased and stripped of whitespace).
    """
    return name.strip().lower()


async def add_tag(session: AsyncSession, name: str) -> bool:
    """Adds a new tag to the database using the injected session.

    Returns:
        bool: True if added successfully, False if the tag already exists.

    Raises:
        DatabaseError: If an internal database error occurs while attempting to add the
        tag.
    """
    clean_name = _normalize_tag(name)
    tag = Tag(name=clean_name)
    session.add(tag)

    try:
        await session.commit()
        logger.info(f"[tags_service] New tag successfully created: '{clean_name}'")

        return True
    except IntegrityError:
        await session.rollback()
        return False
    except SQLAlchemyError as e:
        await session.rollback()
        logger.exception(f"[tags_service] Error adding tag '{clean_name}'")
        raise DatabaseError(f"Failed to add tag '{clean_name}'") from e


async def get_all_tags(session: AsyncSession) -> list[str]:
    """Retrieves all available tags from the database.

    Returns:
        list[str]: A list of tag names.

    Raises:
        DatabaseError: If a database error occurs while fetching the tags.
    """
    tags = select(Tag.name).order_by(Tag.name)
    try:
        result = await session.execute(tags)
        return list(result.scalars().all())
    except SQLAlchemyError as e:
        logger.exception("[tags_service] Error retrieving tags")
        raise DatabaseError("Failed to fetch all tags from the database") from e


async def delete_tag(session: AsyncSession, name: str) -> bool:
    """Deletes a tag from the database by its name.

    Returns:
        bool: True if deleted, False if the tag was not found

    Raises:
        DatabaseError: If a database transaction fails while attempting to delete the
        tag.
    """
    clean_name = _normalize_tag(name)
    stmt = delete(Tag).where(Tag.name == clean_name)

    try:
        result = await session.execute(stmt)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.exception(f"[tags_service] Error deleting tag '{clean_name}'")
        raise DatabaseError(f"Failed to delete tag '{clean_name}'") from e

    deleted = bool(getattr(result, "rowcount", 0) > 0)
    return deleted
