"""
bot/middlewares/admin_middleware.py — Admin guard decorator.

Use @require_admin on any handler to restrict it to admins only.
"""

from functools import wraps
from typing import Any, Callable

from aiogram.types import Message, CallbackQuery

from config import config


def require_admin(handler: Callable) -> Callable:
    """
    Decorator for handlers that should be admin-only.
    Works on both Message and CallbackQuery handlers.
    """
    @wraps(handler)
    async def wrapper(event: Any, *args, **kwargs):
        user_id = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        if user_id not in config.admin_ids:
            if isinstance(event, Message):
                await event.answer("🚫 Access denied. Admin only.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Access denied.", show_alert=True)
            return

        return await handler(event, *args, **kwargs)

    return wrapper
