"""
bot/services/transaction_service.py — Transaction CRUD and business logic.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.category import CategoryType
from database.models.transaction import Transaction


async def add_transaction(
    session: AsyncSession,
    type_: CategoryType,
    amount_dollars: float,
    category_id: int,
    description: str | None,
    created_by: int,
) -> Transaction:
    """
    Persist a new transaction.
    Dollar amount is converted to cents to avoid float precision issues.
    """
    tx = Transaction(
        type=type_,
        amount_cents=round(amount_dollars * 100),
        category_id=category_id,
        description=description,
        created_by=created_by,
    )
    session.add(tx)
    await session.flush()
    return tx


async def delete_transaction(session: AsyncSession, tx_id: int) -> bool:
    """Soft-delete a transaction. Returns False if not found."""
    result = await session.execute(
        select(Transaction).where(Transaction.id == tx_id, Transaction.is_deleted == False)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        return False
    tx.is_deleted = True
    tx.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def get_recent_transactions(
    session: AsyncSession, limit: int = 10, offset: int = 0
) -> list[Transaction]:
    """Return recent non-deleted transactions with category eagerly loaded."""
    result = await session.execute(
        select(Transaction)
        .options(selectinload(Transaction.category_rel), selectinload(Transaction.creator))
        .where(Transaction.is_deleted == False)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_transaction_by_id(session: AsyncSession, tx_id: int) -> Transaction | None:
    result = await session.execute(
        select(Transaction)
        .options(selectinload(Transaction.category_rel))
        .where(Transaction.id == tx_id, Transaction.is_deleted == False)
    )
    return result.scalar_one_or_none()
