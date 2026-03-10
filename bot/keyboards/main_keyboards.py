"""
bot/keyboards/main_keyboards.py — All inline and reply keyboards.

Keyboards are pure functions returning InlineKeyboardMarkup / ReplyKeyboardMarkup.
They accept data from services (e.g. category list) to build dynamic buttons.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from database.models.category import Category, CategoryType


# ──────────────────────────────────────────────
# Admin main menu
# ──────────────────────────────────────────────

def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Daromad qo'shish", callback_data="add_income"),
        InlineKeyboardButton(text="💸 Xarajat qo'shish", callback_data="add_expense"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Tranzaksiyalar", callback_data="view_transactions"),
        InlineKeyboardButton(text="📊 Statistika", callback_data="view_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="🗂 Kategoriyalar", callback_data="manage_categories"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Category selection
# ──────────────────────────────────────────────

def category_keyboard(
    categories: list[Category], action_prefix: str
) -> InlineKeyboardMarkup:
    """
    Build a keyboard of category buttons.
    action_prefix: e.g. "cat_income" → callback_data = "cat_income:3"
    """
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=cat.name,
            callback_data=f"{action_prefix}:{cat.id}",
        )
    builder.adjust(2)  # 2 buttons per row
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()


# ──────────────────────────────────────────────
# Transaction management
# ──────────────────────────────────────────────

def transaction_actions_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_tx:{tx_id}"),
        InlineKeyboardButton(text="🔙 Ortga", callback_data="view_transactions"),
    )
    return builder.as_markup()


def confirm_delete_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_del:{tx_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="view_transactions"),
    )
    return builder.as_markup()


def transactions_list_keyboard(
    transactions: list, page: int = 0, per_page: int = 10, total: int = 0
) -> InlineKeyboardMarkup:
    """Keyboard for transaction list with pagination and per-item detail buttons."""
    builder = InlineKeyboardBuilder()

    for tx in transactions:
        icon = "💰" if tx.type.value == "income" else "💸"
        label = f"{icon} #{tx.id} ${tx.amount:.2f} — {tx.category_rel.name}"
        builder.button(text=label, callback_data=f"tx_detail:{tx.id}")

    builder.adjust(1)

    # Pagination row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀ Oldingi", callback_data=f"tx_page:{page - 1}")
        )
    if (page + 1) * per_page < total:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ▶", callback_data=f"tx_page:{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="🔙 Menyu", callback_data="admin_menu"))
    return builder.as_markup()


# ──────────────────────────────────────────────
# Category management
# ──────────────────────────────────────────────

def manage_categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Daromad kategoriyasi", callback_data="add_cat:income"),
        InlineKeyboardButton(text="➕ Xarajat kategoriyasi", callback_data="add_cat:expense"),
    )
    for cat in categories:
        icon = "🟢" if cat.type == CategoryType.income else "🔴"
        builder.button(
            text=f"{icon} {cat.name}",
            callback_data=f"del_cat:{cat.id}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Menyu", callback_data="admin_menu"))
    return builder.as_markup()


# ──────────────────────────────────────────────
# General
# ──────────────────────────────────────────────

def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Menyuga qaytish", callback_data="admin_menu")
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="cancel")
    return builder.as_markup()
