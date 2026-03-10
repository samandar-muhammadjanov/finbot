"""
bot/utils/formatters.py — Pure functions that turn data into Telegram-ready strings.

No DB calls here — just string formatting.
All monetary values come in as floats (dollars).
"""

from bot.services.stats_service import FullStats
from database.models.transaction import Transaction
from config import config


def fmt_money(amount: float) -> str:
    """Format an amount in Uzbek som with thousands separator."""
    return f"{amount:,.0f} so'm"


def fmt_stats(stats: FullStats) -> str:
    """Format full statistics into a clean Telegram message."""
    s = stats.all_time
    today = stats.today
    month = stats.this_month

    lines = [
        f"📊 *{config.company_name} — Moliyaviy Statistika*",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🏦 *Barcha vaqt*",
        f"  💰 Jami daromad:  `{fmt_money(s.total_income)}`",
        f"  💸 Jami xarajat:  `{fmt_money(s.total_expense)}`",
        f"  📈 Balans:        `{fmt_money(s.balance)}`",
        "",
        "📅 *Bugun*",
        f"  💰 Daromad:  `{fmt_money(today.total_income)}`",
        f"  💸 Xarajat:  `{fmt_money(today.total_expense)}`",
        f"  📈 Balans:   `{fmt_money(today.balance)}`",
        "",
        "🗓 *Bu oy*",
        f"  💰 Daromad:  `{fmt_money(month.total_income)}`",
        f"  💸 Xarajat:  `{fmt_money(month.total_expense)}`",
        f"  📈 Balans:   `{fmt_money(month.balance)}`",
    ]

    if stats.top_expense_categories:
        lines += ["", "🔴 *Eng ko'p xarajat kategoriyalari*"]
        for i, (name, amt) in enumerate(stats.top_expense_categories, 1):
            lines.append(f"  {i}. {name}: `{fmt_money(amt)}`")

    if stats.top_income_categories:
        lines += ["", "🟢 *Eng ko'p daromad kategoriyalari*"]
        for i, (name, amt) in enumerate(stats.top_income_categories, 1):
            lines.append(f"  {i}. {name}: `{fmt_money(amt)}`")

    return "\n".join(lines)


def fmt_transaction_list(transactions: list[Transaction], title: str = "So'nggi tranzaksiyalar") -> str:
    """Format a list of transactions into a readable message."""
    if not transactions:
        return f"📭 *{title}*\n\nTranzaksiyalar topilmadi."

    lines = [f"📋 *{title}*", ""]
    for tx in transactions:
        icon = "💰" if tx.type.value == "income" else "💸"
        cat_name = tx.category_rel.name if tx.category_rel else "Noma'lum"
        desc = f" — {tx.description}" if tx.description else ""
        date_str = tx.created_at.strftime("%d %b %Y")
        lines.append(
            f"{icon} `#{tx.id}` | `{fmt_money(tx.amount)}` | *{cat_name}*{desc} _{date_str}_"
        )

    return "\n".join(lines)


def fmt_single_transaction(tx: Transaction) -> str:
    """Format a single transaction detail card."""
    icon = "💰" if tx.type.value == "income" else "💸"
    cat_name = tx.category_rel.name if tx.category_rel else "Noma'lum"
    creator = tx.creator.full_name if tx.creator else "Noma'lum"
    type_name = "Daromad" if tx.type.value == "income" else "Xarajat"

    return (
        f"{icon} *Tranzaksiya #{tx.id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Turi:        `{type_name}`\n"
        f"Summa:       `{fmt_money(tx.amount)}`\n"
        f"Kategoriya:  `{cat_name}`\n"
        f"Izoh:        `{tx.description or '—'}`\n"
        f"Qo'shgan:    `{creator}`\n"
        f"Sana:        `{tx.created_at.strftime('%d %b %Y %H:%M UTC')}`"
    )
