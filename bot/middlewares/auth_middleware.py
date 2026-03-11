"""
bot/middlewares/auth_middleware.py — Block unauthenticated users.

Runs after DatabaseMiddleware (which sets db_user).
Admins are always allowed through.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message


class AuthMiddleware(BaseMiddleware):
    """
    Gate: only let authenticated users (or admins) through to handlers.
    Unauthenticated users only reach the auth router (Login FSM).
    """

    # These are allowed even without authentication
    OPEN_COMMANDS = {"/start"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        db_user = data.get("db_user")

        # Always allow: no user (webhooks, channel posts) or admin or authenticated
        if db_user is None or db_user.is_admin or db_user.is_authenticated:
            return await handler(event, data)

        # Allow /start command and Login FSM states through
        if isinstance(event, Message):
            text = (event.text or "").strip().lower()
            if text.startswith("/start"):
                return await handler(event, data)

        # Check FSM — allow login states through
        state = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state and current_state.startswith("Login:"):
                return await handler(event, data)

        # Block everything else — but still call the handler so the
        # auth router's catch-all can reply
        return await handler(event, data)
