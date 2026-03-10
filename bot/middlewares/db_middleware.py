"""
bot/middlewares/db_middleware.py — Database session middleware.

Injects an AsyncSession into every handler via handler data dict.
Also upserts the Telegram user record on every interaction.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from database.engine import get_session
from bot.services.user_service import upsert_user


class DatabaseMiddleware(BaseMiddleware):
    """
    Attaches a fresh DB session to each update.

    Handlers access it via: session = data["session"]
    User object is also pre-loaded: db_user = data["db_user"]
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with get_session() as session:
            data["session"] = session

            # Upsert user if we have a Telegram user object
            tg_user = data.get("event_from_user")
            if tg_user:
                db_user = await upsert_user(session, tg_user)
                data["db_user"] = db_user
            else:
                data["db_user"] = None

            return await handler(event, data)
