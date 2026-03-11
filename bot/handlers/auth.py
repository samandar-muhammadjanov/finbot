"""
bot/handlers/auth.py — Login FSM for non-admin users.

Flow:
  /start (unauthenticated) → asks username → asks password → success/fail

All handlers here use the `not_authenticated` filter so they only fire for
users who haven't logged in yet. Authenticated users pass through to the
common/stats/admin routers.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.models.user import User

router = Router(name="auth")

MAX_ATTEMPTS = 3


class Login(StatesGroup):
    waiting_username = State()
    waiting_password = State()


# ── Filter: only match users who are NOT authenticated ──

async def not_authenticated(message: Message, db_user: User | None) -> bool:
    if db_user is None:
        return True
    return not db_user.is_authenticated and not db_user.is_admin


# ── /start for unauthenticated users ──

@router.message(not_authenticated, Command("start"))
async def start_login(message: Message, state: FSMContext):
    """Begin login flow for unauthenticated non-admin users."""
    await state.set_state(Login.waiting_username)
    await state.update_data(attempts=0)
    await message.answer(
        "👋 *Xush kelibsiz!*\n\n"
        "🔐 Davom etish uchun tizimga kirishingiz kerak.\n\n"
        "Foydalanuvchi nomingizni kiriting:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Login.waiting_username)
async def got_username(message: Message, state: FSMContext):
    username = (message.text or "").strip()
    if not username:
        await message.answer("⚠️ Iltimos, foydalanuvchi nomingizni kiriting:")
        return

    await state.update_data(username=username)
    await state.set_state(Login.waiting_password)
    await message.answer(
        f"🔑 *{username}* uchun parolni kiriting:",
        parse_mode="Markdown",
    )


@router.message(Login.waiting_password)
async def got_password(message: Message, state: FSMContext, session: AsyncSession, db_user: User | None):
    data = await state.get_data()
    username = data.get("username", "")
    password = (message.text or "").strip()
    attempts = data.get("attempts", 0) + 1

    # Delete the password message for security
    try:
        await message.delete()
    except Exception:
        pass

    # Validate credentials
    expected_password = config.bot_users.get(username)
    if expected_password and expected_password == password:
        # ✅ Success
        await state.clear()
        if db_user:
            db_user.is_authenticated = True
            await session.flush()

        name = message.from_user.first_name if message.from_user else username
        user_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📋 Tranzaksiyalar")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            f"✅ *Muvaffaqiyatli kirdingiz!*\n\n"
            f"Salom, *{name}*! 👋\n"
            "Endi moliyaviy ma'lumotlarni ko'rishingiz mumkin.\n\n"
            "📊 /stats — Statistika\n"
            "📋 /transactions — Tranzaksiyalar\n"
            "❓ /help — Yordam",
            parse_mode="Markdown",
            reply_markup=user_menu,
        )
    else:
        # ❌ Wrong credentials
        if attempts >= MAX_ATTEMPTS:
            await state.clear()
            await message.answer(
                "❌ *Juda ko'p noto'g'ri urinish.*\n\n"
                "Qaytadan urinish uchun /start yozing.",
                parse_mode="Markdown",
            )
        else:
            remaining = MAX_ATTEMPTS - attempts
            await state.update_data(attempts=attempts)
            await state.set_state(Login.waiting_username)
            await message.answer(
                f"❌ *Login yoki parol noto'g'ri.*\n"
                f"Qayta urinib ko'ring. Urinishlar qoldi: *{remaining}*\n\n"
                "Foydalanuvchi nomingizni qayta kiriting:",
                parse_mode="Markdown",
            )


# ── Catch-all: block unauthenticated users from other text commands ──

@router.message(not_authenticated, F.text)
async def block_unauthenticated(message: Message):
    """Block all non-FSM messages from unauthenticated users."""
    await message.answer(
        "🔒 Ushbu botdan foydalanish uchun tizimga kirishingiz kerak.\n\n"
        "/start — Tizimga kirish",
    )
