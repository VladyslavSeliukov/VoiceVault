from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from modules.tags.service import add_tag, delete_tag, get_all_tags
from modules.telegram.templates import UI

router = Router()


@router.message(Command("tags"))
async def list_tags(message: Message, session: AsyncSession) -> None:
    """Handle the /tags command to display all allowed taxonomy tags."""
    tags = await get_all_tags(session)
    if not tags:
        await message.answer(UI.TAGS_EMPTY)
        return

    tags_list = "\n".join(f"- {tag}" for tag in tags)
    await message.answer(UI.TAGS_LIST.format(tags=tags_list))


@router.message(Command("add_tag"))
async def handle_add_tag(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Handle the /add_tag command to register a new allowed tag."""
    if not command.args:
        await message.answer(UI.TAG_ADD_USAGE)
        return

    tag_name = command.args
    success = await add_tag(session, tag_name)

    if success:
        await message.answer(UI.TAG_ADDED.format(tag=tag_name))
    else:
        await message.answer(UI.TAG_EXISTS.format(tag=tag_name))


@router.message(Command("del_tag"))
async def handle_del_tag(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Handle the /del_tag command to remove a tag from the database."""
    if not command.args:
        await message.answer(UI.TAG_DEL_USAGE)
        return

    tag_name = command.args
    success = await delete_tag(session, tag_name)

    if success:
        await message.answer(UI.TAG_DELETED.format(tag=tag_name))
    else:
        await message.answer(UI.TAG_NOT_FOUND.format(tag=tag_name))
