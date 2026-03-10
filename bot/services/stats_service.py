"""
bot/services/stats_service.py — Financial statistics calculations.

All queries are async and return plain Python dicts for easy formatting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.category import CategoryType
from database.models.transaction import Transaction
from database.models.category import Category


@dataclass
class PeriodStats:
    total_income: float = 0.0
    total_expense: float = 0.0
    transaction_count: int = 0

    @property
    def balance(self) -> float:
        return self.total_income - self.total_expense


@dataclass
class FullStats:
    all_time: PeriodStats = field(default_factory=PeriodStats)
    today: PeriodStats = field(default_factory=PeriodStats)
    this_month: PeriodStats = field(default_factory=PeriodStats)
    top_expense_categories: List[Tuple[str, float]] = field(default_factory=list)
    top_income_categories: List[Tuple[str, float]] = field(default_factory=list)


async def _period_stats(
    session: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
) -> PeriodStats:
    """Calculate income/expense totals for a given time window."""
    base = select(
        Transaction.type,
        func.sum(Transaction.amount_cents).label("total"),
        func.count(Transaction.id).label("cnt"),
    ).where(Transaction.is_deleted == False)

    if start:
        base = base.where(Transaction.created_at >= start)
    if end:
        base = base.where(Transaction.created_at <= end)

    base = base.group_by(Transaction.type)
    result = await session.execute(base)
    rows = result.all()

    stats = PeriodStats()
    for row in rows:
        dollars = row.total / 100
        stats.transaction_count += row.cnt
        if row.type == CategoryType.income:
            stats.total_income = dollars
        else:
            stats.total_expense = dollars

    return stats


async def _top_categories(
    session: AsyncSession,
    type_: CategoryType,
    limit: int = 5,
    start: datetime | None = None,
) -> List[Tuple[str, float]]:
    """Return top N categories by total amount for a given type."""
    query = (
        select(
            Category.name,
            func.sum(Transaction.amount_cents).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(Transaction.is_deleted == False, Transaction.type == type_)
    )
    if start:
        query = query.where(Transaction.created_at >= start)

    query = query.group_by(Category.name).order_by(func.sum(Transaction.amount_cents).desc()).limit(limit)

    result = await session.execute(query)
    return [(row.name, row.total / 100) for row in result.all()]


async def get_full_stats(session: AsyncSession) -> FullStats:
    """Compute all statistics needed for the /stats command."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    all_time = await _period_stats(session)
    today = await _period_stats(session, start=today_start)
    this_month = await _period_stats(session, start=month_start)
    top_expense = await _top_categories(session, CategoryType.expense)
    top_income = await _top_categories(session, CategoryType.income)

    return FullStats(
        all_time=all_time,
        today=today,
        this_month=this_month,
        top_expense_categories=top_expense,
        top_income_categories=top_income,
    )
