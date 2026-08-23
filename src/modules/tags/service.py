from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    """
    clean_name = _normalize_tag(name)
    tag = Tag(name=clean_name)
    session.add(tag)

    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False
    except Exception as e:
        await session.rollback()
        logger.error(f"[tags_service] Error adding tag '{clean_name}': {e}")
        raise


async def get_all_tags(session: AsyncSession) -> list[str]:
    """Retrieves all available tags from the database.

    Returns:
        list[str]: A list of tag names.
    """
    tags = select(Tag.name).order_by(Tag.name)
    result = await session.execute(tags)
    return list(result.scalars().all())


async def delete_tag(session: AsyncSession, name: str) -> bool:
    """Deletes a tag from the database by its name.

    Returns:
        bool: True if deleted, False if the tag was not found.
    """
    clean_name = _normalize_tag(name)
    stmt = delete(Tag).where(Tag.name == clean_name)
    result = await session.execute(stmt)
    await session.commit()

    return bool(getattr(result, "rowcount", 0) > 0)
