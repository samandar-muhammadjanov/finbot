"""
bot/handlers/stats.py — Statistics and transaction history commands.

Available to all users.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services import get_full_stats, get_recent_transactions
from bot.utils import fmt_stats, fmt_transaction_list

router = Router(name="stats")
PER_PAGE = 10


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Display full financial statistics."""
    await message.answer("⏳ Statistika hisoblanmoqda...")

    stats = await get_full_stats(session)
    text = fmt_stats(stats)
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("transactions"))
async def cmd_transactions(message: Message, session: AsyncSession):
    """Display the 10 most recent transactions."""
    transactions = await get_recent_transactions(session, limit=PER_PAGE)
    text = fmt_transaction_list(transactions)
    await message.answer(text, parse_mode="Markdown")
