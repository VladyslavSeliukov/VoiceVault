from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from modules.tags.service import add_tag, delete_tag, get_all_tags

pytestmark = pytest.mark.asyncio


class TestTagOperations:
    """Tests for tag creation, normalization, and retrieval."""

    async def test_tag_normalization_and_addition(
        self, db_transaction: AsyncSession
    ) -> None:
        """Verifies that tags are stripped of whitespace and converted to lowercase."""
        success_1: bool = await add_tag(db_transaction, "  Python  ")
        success_2: bool = await add_tag(db_transaction, "FASTAPI")

        assert success_1 is True
        assert success_2 is True

        tags: list[str] = await get_all_tags(db_transaction)
        assert "python" in tags
        assert "fastapi" in tags

    async def test_duplicate_tag_prevention(self, db_transaction: AsyncSession) -> None:
        """Verify adding a duplicate tag (case-insensitive) returns False."""
        first_attempt: bool = await add_tag(db_transaction, "architecture")
        assert first_attempt is True

        second_attempt: bool = await add_tag(db_transaction, "ARCHITECTURE")
        assert second_attempt is False


class TestTagDeletion:
    """Tests for tag removal logic."""

    async def test_delete_existing_tag(self, db_transaction: AsyncSession) -> None:
        """Verifies successful deletion of an existing tag."""
        await add_tag(db_transaction, "to_delete")

        deleted: bool = await delete_tag(db_transaction, "to_delete")
        assert deleted is True

        tags: list[str] = await get_all_tags(db_transaction)
        assert "to_delete" not in tags

    async def test_delete_non_existent_tag(self, db_transaction: AsyncSession) -> None:
        """Verifies that attempting to delete a missing tag safely returns False."""
        deleted: bool = await delete_tag(db_transaction, "does_not_exist")
        assert deleted is False


class TestDatabaseErrorHandling:
    """Tests for safe error propagation during database transaction failures."""

    async def test_add_tag_database_error(
        self, db_transaction: AsyncSession, mocker: Any
    ) -> None:
        """Verifies DatabaseError is raised when tag addition fails at the DB level."""
        mocker.patch.object(
            db_transaction, "commit", side_effect=SQLAlchemyError("Connection lost")
        )

        with pytest.raises(DatabaseError, match="Failed to add tag 'crash_test'"):
            await add_tag(db_transaction, "crash_test")

    async def test_get_all_tags_database_error(
        self, db_transaction: AsyncSession, mocker: Any
    ) -> None:
        """Verifies DatabaseError is raised when tag retrieval fails at the DB level."""
        mocker.patch.object(
            db_transaction, "execute", side_effect=SQLAlchemyError("Connection lost")
        )

        with pytest.raises(
            DatabaseError, match="Failed to fetch all tags from the database"
        ):
            await get_all_tags(db_transaction)

    async def test_delete_tag_database_error(
        self, db_transaction: AsyncSession, mocker: Any
    ) -> None:
        """Verifies DatabaseError is raised when tag deletion fails at the DB level."""
        mocker.patch.object(
            db_transaction, "execute", side_effect=SQLAlchemyError("Connection lost")
        )

        with pytest.raises(DatabaseError, match="Failed to delete tag 'to_delete'"):
            await delete_tag(db_transaction, "to_delete")
