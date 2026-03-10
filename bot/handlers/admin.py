"""
bot/handlers/admin.py — Admin panel using aiogram FSM.

Transaction creation flow (FSM states):
  AddTransaction.choosing_type      ← /add_income or /add_expense
  AddTransaction.choosing_category  ← user selects category via inline button
  AddTransaction.entering_amount    ← user types amount
  AddTransaction.entering_desc      ← user types description (or skips)

Category management flow:
  AddCategory.choosing_type         ← admin selects income/expense type
  AddCategory.entering_name         ← admin types category name
"""

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    admin_menu_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    category_keyboard,
    confirm_delete_keyboard,
    manage_categories_keyboard,
    transaction_actions_keyboard,
    transactions_list_keyboard,
)
from bot.middlewares import require_admin
from bot.services import (
    add_category,
    add_transaction,
    deactivate_category,
    delete_transaction,
    get_categories,
    get_recent_transactions,
    get_transaction_by_id,
    get_full_stats,
    get_all_users,
)
from bot.utils import fmt_single_transaction, fmt_stats, fmt_transaction_list
from database.models.category import CategoryType
from database.models.user import User

router = Router(name="admin")
PER_PAGE = 10


# ══════════════════════════════════════════════
# FSM State groups
# ══════════════════════════════════════════════

class AddTransaction(StatesGroup):
    choosing_category = State()
    entering_amount = State()
    entering_desc = State()


class AddCategory(StatesGroup):
    entering_name = State()


# ══════════════════════════════════════════════
# Admin menu
# ══════════════════════════════════════════════

@router.message(Command("admin"))
@require_admin
async def cmd_admin(message: Message):
    await message.answer(
        "👑 *Admin Panel*\nAmalni tanlang:",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_menu")
@require_admin
async def cb_admin_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "👑 *Admin Panel*\nAmalni tanlang:",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )
    await call.answer()


# ══════════════════════════════════════════════
# Add Income / Expense — entry points
# ══════════════════════════════════════════════

@router.message(Command("add_income"))
@require_admin
async def cmd_add_income(message: Message, state: FSMContext, session: AsyncSession):
    await _start_add_transaction(message, state, session, CategoryType.income)


@router.message(Command("add_expense"))
@require_admin
async def cmd_add_expense(message: Message, state: FSMContext, session: AsyncSession):
    await _start_add_transaction(message, state, session, CategoryType.expense)


@router.callback_query(F.data == "add_income")
@require_admin
async def cb_add_income(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await call.message.delete()
    await _start_add_transaction(call.message, state, session, CategoryType.income)
    await call.answer()


@router.callback_query(F.data == "add_expense")
@require_admin
async def cb_add_expense(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await call.message.delete()
    await _start_add_transaction(call.message, state, session, CategoryType.expense)
    await call.answer()


async def _start_add_transaction(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    tx_type: CategoryType,
):
    categories = await get_categories(session, type_filter=tx_type)
    if not categories:
        type_name = "daromad" if tx_type == CategoryType.income else "xarajat"
        await message.answer(
            f"⚠️ *{type_name}* uchun kategoriyalar topilmadi.\n"
            "Avval /categories orqali kategoriya qo'shing.",
            parse_mode="Markdown",
        )
        return

    await state.update_data(tx_type=tx_type.value)
    await state.set_state(AddTransaction.choosing_category)

    icon = "💰" if tx_type == CategoryType.income else "💸"
    type_name = "Daromad" if tx_type == CategoryType.income else "Xarajat"
    await message.answer(
        f"{icon} *{type_name} qo'shish*\n\nKategoriyani tanlang:",
        parse_mode="Markdown",
        reply_markup=category_keyboard(categories, action_prefix="cat_sel"),
    )


# ══════════════════════════════════════════════
# FSM Step 1 — Category selected
# ══════════════════════════════════════════════

@router.callback_query(AddTransaction.choosing_category, F.data.startswith("cat_sel:"))
async def cb_category_selected(call: CallbackQuery, state: FSMContext):
    category_id = int(call.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(AddTransaction.entering_amount)

    await call.message.edit_text(
        "💵 *Summani* kiriting (masalan: `1500` yoki `12.50`):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


# ══════════════════════════════════════════════
# FSM Step 2 — Amount entered
# ══════════════════════════════════════════════

@router.message(AddTransaction.entering_amount)
async def fsm_amount_entered(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer(
            "⚠️ Noto'g'ri summa. Musbat son kiriting (masalan: `500` yoki `12.50`):",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(AddTransaction.entering_desc)

    await message.answer(
        "📝 *Izoh* kiriting (sabab/eslatma) yoki bo'sh qoldirish uchun /skip yozing:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


# ══════════════════════════════════════════════
# FSM Step 3 — Description entered (or skipped)
# ══════════════════════════════════════════════

@router.message(AddTransaction.entering_desc, Command("skip"))
async def fsm_desc_skip(message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot):
    await _finalize_transaction(message, state, session, db_user, description=None, bot=bot)


@router.message(AddTransaction.entering_desc)
async def fsm_desc_entered(message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot):
    description = message.text.strip() if message.text else None
    await _finalize_transaction(message, state, session, db_user, description=description, bot=bot)


async def _finalize_transaction(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
    description: str | None,
    bot: Bot,
):
    """Save transaction to DB, confirm to admin, and notify all users."""
    data = await state.get_data()
    await state.clear()

    tx_type = CategoryType(data["tx_type"])
    amount = data["amount"]
    category_id = data["category_id"]

    tx = await add_transaction(
        session=session,
        type_=tx_type,
        amount_dollars=amount,
        category_id=category_id,
        description=description,
        created_by=db_user.id,
    )

    # Reload with relationships for display
    tx = await get_transaction_by_id(session, tx.id)
    icon = "💰" if tx_type == CategoryType.income else "💸"
    type_name = "Daromad" if tx_type == CategoryType.income else "Xarajat"
    cat_name = tx.category_rel.name if tx.category_rel else "?"

    confirmation = (
        f"✅ *Tranzaksiya saqlandi!*\n\n"
        f"{icon} *{type_name}*: `{amount:,.0f} so'm`\n"
        f"📂 Kategoriya: `{cat_name}`\n"
        f"📝 Izoh: `{description or '—'}`\n"
        f"🆔 Tranzaksiya ID: `#{tx.id}`"
    )
    await message.answer(confirmation, parse_mode="Markdown", reply_markup=admin_menu_keyboard())

    # ── Broadcast to all non-admin users ──
    notify_text = (
        f"🔔 *Yangi {type_name.lower()} qo'shildi!*\n\n"
        f"{icon} *Summa*: `{amount:,.0f} so'm`\n"
        f"📂 *Kategoriya*: `{cat_name}`\n"
        f"📝 *Izoh*: `{description or '—'}`"
    )
    all_users = await get_all_users(session)
    for user in all_users:
        try:
            await bot.send_message(user.id, notify_text, parse_mode="Markdown")
        except Exception:
            pass  # User may have blocked the bot


# ══════════════════════════════════════════════
# View Transactions (admin inline)
# ══════════════════════════════════════════════

@router.callback_query(F.data == "view_transactions")
@require_admin
async def cb_view_transactions(call: CallbackQuery, session: AsyncSession):
    await _send_transaction_page(call, session, page=0)
    await call.answer()


@router.callback_query(F.data.startswith("tx_page:"))
@require_admin
async def cb_tx_page(call: CallbackQuery, session: AsyncSession):
    page = int(call.data.split(":")[1])
    await _send_transaction_page(call, session, page=page)
    await call.answer()


async def _send_transaction_page(call: CallbackQuery, session: AsyncSession, page: int):
    offset = page * PER_PAGE
    transactions = await get_recent_transactions(session, limit=PER_PAGE, offset=offset)

    # Get total count for pagination (reuse service with large limit)
    all_txs = await get_recent_transactions(session, limit=9999)
    total = len(all_txs)

    if not transactions:
        await call.message.edit_text(
            "📭 Tranzaksiyalar topilmadi.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    text = f"📋 *Tranzaksiyalar* ({page + 1}-sahifa)\nBatafsil ko'rish uchun tanlang."
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=transactions_list_keyboard(transactions, page=page, per_page=PER_PAGE, total=total),
    )


@router.callback_query(F.data.startswith("tx_detail:"))
@require_admin
async def cb_tx_detail(call: CallbackQuery, session: AsyncSession):
    tx_id = int(call.data.split(":")[1])
    tx = await get_transaction_by_id(session, tx_id)

    if not tx:
        await call.answer("Tranzaksiya topilmadi.", show_alert=True)
        return

    text = fmt_single_transaction(tx)
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=transaction_actions_keyboard(tx_id),
    )
    await call.answer()


# ══════════════════════════════════════════════
# Delete Transaction
# ══════════════════════════════════════════════

@router.message(Command("del_tx"))
@require_admin
async def cmd_del_tx(message: Message, session: AsyncSession):
    """Delete via command: /del_tx 42"""
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /del\\_tx \\<tranzaksiya\\_id\\>", parse_mode="MarkdownV2")
        return

    tx_id = int(parts[1])
    deleted = await delete_transaction(session, tx_id)

    if deleted:
        await message.answer(f"✅ `#{tx_id}` tranzaksiya o'chirildi.", parse_mode="Markdown")
    else:
        await message.answer(f"❌ `#{tx_id}` tranzaksiya topilmadi.", parse_mode="Markdown")


@router.callback_query(F.data.startswith("del_tx:"))
@require_admin
async def cb_del_tx(call: CallbackQuery):
    tx_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        f"⚠️ *#{tx_id}* tranzaksiyani o'chirishni tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=confirm_delete_keyboard(tx_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm_del:"))
@require_admin
async def cb_confirm_delete(call: CallbackQuery, session: AsyncSession):
    tx_id = int(call.data.split(":")[1])
    deleted = await delete_transaction(session, tx_id)

    if deleted:
        await call.message.edit_text(
            f"✅ `#{tx_id}` tranzaksiya o'chirildi.",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await call.message.edit_text(
            f"❌ `#{tx_id}` tranzaksiya topilmadi yoki allaqachon o'chirilgan.",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard(),
        )
    await call.answer()


# ══════════════════════════════════════════════
# View Stats (admin inline)
# ══════════════════════════════════════════════

@router.callback_query(F.data == "view_stats")
@require_admin
async def cb_view_stats(call: CallbackQuery, session: AsyncSession):
    stats = await get_full_stats(session)
    text = fmt_stats(stats)
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()


# ══════════════════════════════════════════════
# Category Management
# ══════════════════════════════════════════════

@router.message(Command("categories"))
@require_admin
async def cmd_categories(message: Message, session: AsyncSession):
    categories = await get_categories(session)
    await message.answer(
        "🗂 *Kategoriyalar boshqaruvi*\nO'chirish uchun tanlang yoki yangi qo'shing:",
        parse_mode="Markdown",
        reply_markup=manage_categories_keyboard(categories),
    )


@router.callback_query(F.data == "manage_categories")
@require_admin
async def cb_manage_categories(call: CallbackQuery, session: AsyncSession):
    categories = await get_categories(session)
    await call.message.edit_text(
        "🗂 *Kategoriyalar boshqaruvi*\nO'chirish uchun tanlang yoki yangi qo'shing:",
        parse_mode="Markdown",
        reply_markup=manage_categories_keyboard(categories),
    )
    await call.answer()


@router.callback_query(F.data.startswith("add_cat:"))
@require_admin
async def cb_add_category_start(call: CallbackQuery, state: FSMContext):
    cat_type = call.data.split(":")[1]  # "income" or "expense"
    type_name = "daromad" if cat_type == "income" else "xarajat"
    await state.update_data(cat_type=cat_type)
    await state.set_state(AddCategory.entering_name)
    await call.message.edit_text(
        f"✏️ Yangi *{type_name}* kategoriyasi nomini kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


@router.message(AddCategory.entering_name)
@require_admin
async def fsm_category_name(message: Message, state: FSMContext, session: AsyncSession):
    name = message.text.strip() if message.text else ""
    if not name or len(name) > 64:
        await message.answer(
            "⚠️ Kategoriya nomi 1 dan 64 belgigacha bo'lishi kerak.",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    await state.clear()

    cat_type = CategoryType(data["cat_type"])
    type_name = "daromad" if cat_type == CategoryType.income else "xarajat"
    try:
        cat = await add_category(session, name=name, type_=cat_type)
        await message.answer(
            f"✅ *{cat.name}* ({type_name}) kategoriyasi muvaffaqiyatli qo'shildi!",
            parse_mode="Markdown",
            reply_markup=admin_menu_keyboard(),
        )
    except ValueError as e:
        await message.answer(f"⚠️ {e}", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("del_cat:"))
@require_admin
async def cb_delete_category(call: CallbackQuery, session: AsyncSession):
    cat_id = int(call.data.split(":")[1])
    deleted = await deactivate_category(session, cat_id)

    if deleted:
        categories = await get_categories(session)
        await call.message.edit_text(
            "✅ Kategoriya o'chirildi.\n\n🗂 *Kategoriyalar boshqaruvi*:",
            parse_mode="Markdown",
            reply_markup=manage_categories_keyboard(categories),
        )
    else:
        await call.answer("Kategoriya topilmadi.", show_alert=True)

    await call.answer()


# ══════════════════════════════════════════════
# Cancel / generic fallback
# ══════════════════════════════════════════════

@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "❌ Amal bekor qilindi.",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()
