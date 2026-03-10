"""
bot/handlers/common.py — Public commands available to all users.

/start — greet user, show role-specific menu
/help  — list available commands
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import admin_menu_keyboard
from config import config
from database.models.user import User

router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, db_user: User):
    """Welcome message — shows admin panel button for admins."""
    name = message.from_user.first_name if message.from_user else "foydalanuvchi"
    role = "👑 Admin" if db_user and db_user.is_admin else "👤 Foydalanuvchi"

    text = (
        f"👋 Salom, *{name}*!\n\n"
        f"*{config.company_name} Finance Bot*ga xush kelibsiz\n"
        f"Sizning rolingiz: {role}\n\n"
        f"Mavjud buyruqlarni ko'rish uchun /help yozing."
    )

    if db_user and db_user.is_admin:
        await message.answer(text, parse_mode="Markdown", reply_markup=admin_menu_keyboard())
    else:
        await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User):
    """Show available commands based on user role."""
    user_commands = (
        "📖 *Mavjud buyruqlar*\n\n"
        "👤 *Foydalanuvchi buyruqlari:*\n"
        "  /start — Botni ishga tushirish\n"
        "  /stats — Moliyaviy statistikani ko'rish\n"
        "  /transactions — So'nggi tranzaksiyalarni ko'rish\n"
        "  /help — Ushbu xabarni ko'rish\n"
    )

    admin_commands = (
        "\n👑 *Admin buyruqlari:*\n"
        "  /admin — Admin panelni ochish\n"
        "  /add\\_income — Daromad qo'shish\n"
        "  /add\\_expense — Xarajat qo'shish\n"
        "  /del\\_tx \\<id\\> — Tranzaksiyani o'chirish\n"
        "  /categories — Kategoriyalarni boshqarish\n"
    )

    text = user_commands
    if db_user and db_user.is_admin:
        text += admin_commands

    await message.answer(text, parse_mode="MarkdownV2")
