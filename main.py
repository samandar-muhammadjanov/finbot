"""
main.py — FinanceBot entry point.

Startup sequence:
  1. Validate config
  2. Initialize database (create tables + seed defaults)
  3. Build aiogram Dispatcher with FSM storage
  4. Register middleware and routers
  5. Start polling (or webhook in production)
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import setup_routers
from bot.middlewares import DatabaseMiddleware
from config import config
from database.engine import init_db

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Run once when the bot starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready.")

    # Notify all admins that the bot has restarted
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"🚀 *{config.company_name} FinanceBot* muvaffaqiyatli ishga tushdi!\n"
                "Admin panelni ochish uchun /admin yozing.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


async def on_shutdown(bot: Bot):
    """Cleanup on graceful shutdown."""
    logger.info("Bot is shutting down...")


async def main():
    config.validate()
    logger.info(f"Starting {config.company_name} FinanceBot...")
    logger.info(f"Admins: {config.admin_ids}")

    # Bot instance with Markdown as default parse mode
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # MemoryStorage is fine for development.
    # For production use RedisStorage:
    #   from aiogram.fsm.storage.redis import RedisStorage
    #   storage = RedisStorage.from_url("redis://localhost:6379")
    storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # ── Middleware (order matters — runs outer→inner) ──
    dp.update.middleware(DatabaseMiddleware())

    # ── Register all route handlers ──
    dp.include_router(setup_routers())

    # ── Lifecycle hooks ──
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Start polling ──
    logger.info("Bot is polling for updates...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
