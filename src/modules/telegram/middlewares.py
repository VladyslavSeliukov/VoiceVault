from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from core.db import AsyncSessionLocal


class DbSessionMiddleware(BaseMiddleware):
    """Middleware to inject an async database session into Telegram handlers.

    Ensures that a single database session is opened per incoming update
    and properly closed after the handler finishes execution.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Execute the middleware to inject an asynchronous database session.

        Wraps the handler execution within an active database session context.
        The session is injected into the `data` dictionary under the `"session"`
        key, making it accessible to subsequent middlewares and the final handler.
        The session is automatically closed when the context manager exits.

        Args:
            handler (Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]): The
                next middleware or the target handler in the aiogram routing chain.
            event (TelegramObject): The incoming Telegram update event.
            data (dict[str, Any]): The context dictionary passed through the chain.

        Returns:
            Any: The return value from the downstream handler.
        """
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)
