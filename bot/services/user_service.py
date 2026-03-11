"""
bot/services/user_service.py — User persistence and admin sync.

Called by the middleware on every update to ensure every
Telegram user is recorded and admin flags are up-to-date.
"""

from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.models.user import User


async def upsert_user(session: AsyncSession, tg_user: TgUser) -> User:
    """
    Insert or update a user record based on Telegram User object.
    Admin flag is derived from config.ADMIN_IDS — source of truth.
    """
    is_admin = tg_user.id in config.admin_ids

    result = await session.execute(select(User).where(User.id == tg_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            is_admin=is_admin,
            is_authenticated=is_admin,  # Admins are auto-authenticated
        )
        session.add(user)
    else:
        # Keep profile in sync with latest Telegram data
        user.username = tg_user.username
        user.full_name = tg_user.full_name
        user.is_admin = is_admin  # reflect config changes without DB migration
        if is_admin:
            user.is_authenticated = True  # promote to authenticated if now admin


    await session.flush()
    return user


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> list[User]:
    """Return all active non-admin users (for broadcasting notifications)."""
    result = await session.execute(
        select(User).where(User.is_active == True, User.is_admin == False)
    )
    return list(result.scalars().all())
