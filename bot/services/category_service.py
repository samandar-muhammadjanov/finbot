"""
bot/services/category_service.py — CRUD for categories.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.category import Category, CategoryType


async def get_categories(
    session: AsyncSession, type_filter: CategoryType | None = None
) -> list[Category]:
    """Return active categories, optionally filtered by type."""
    query = select(Category).where(Category.is_active == True)
    if type_filter:
        query = query.where(Category.type == type_filter)
    query = query.order_by(Category.name)
    result = await session.execute(query)
    return list(result.scalars().all())


async def add_category(
    session: AsyncSession, name: str, type_: CategoryType
) -> Category:
    """Create a new category. Raises ValueError if name already exists."""
    existing = await session.execute(
        select(Category).where(Category.name == name)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Category '{name}' already exists.")

    cat = Category(name=name, type=type_)
    session.add(cat)
    await session.flush()
    return cat


async def deactivate_category(session: AsyncSession, category_id: int) -> bool:
    """Soft-delete a category. Returns False if not found."""
    result = await session.execute(
        select(Category).where(Category.id == category_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        return False
    cat.is_active = False
    await session.flush()
    return True


async def get_category_by_id(session: AsyncSession, category_id: int) -> Category | None:
    result = await session.execute(
        select(Category).where(Category.id == category_id, Category.is_active == True)
    )
    return result.scalar_one_or_none()
