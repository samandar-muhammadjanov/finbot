"""
main.py — FinanceBot entry point.

Startup sequence:
  1. Validate config
  2. Initialize database (create tables + seed defaults)
  3. Start aiohttp Mini App server (if WEBAPP_URL is configured)
  4. Build aiogram Dispatcher with FSM storage
  5. Register middleware and routers
  6. Set Menu Button for admins (opens Mini App)
  7. Start polling
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, MenuButtonDefault, WebAppInfo

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

    # Set Menu Button for admins → opens Mini App (if URL is configured)
    if config.webapp_url:
        for admin_id in config.admin_ids:
            try:
                await bot.set_chat_menu_button(
                    chat_id=admin_id,
                    menu_button=MenuButtonWebApp(
                        text="📊 Admin Panel",
                        web_app=WebAppInfo(url=config.webapp_url),
                    ),
                )
                logger.info(f"Menu button set for admin {admin_id}")
            except Exception as e:
                logger.warning(f"Could not set menu button for admin {admin_id}: {e}")
    else:
        logger.warning("WEBAPP_URL not set — skipping menu button setup.")

    # Notify admins on restart
    for admin_id in config.admin_ids:
        try:
            msg = (
                f"🚀 *{config.company_name} FinanceBot* muvaffaqiyatli ishga tushdi!\n"
                "Admin panelni ochish uchun /admin yozing."
            )
            if config.webapp_url:
                msg += "\n📊 Yoki pastdagi *Admin Panel* tugmasini bosing."
            await bot.send_message(admin_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Cleanup on graceful shutdown."""
    logger.info("Bot is shutting down...")
    
    # Clean up web_runner if it exists
    web_runner = dispatcher.workflow_data.get("web_runner")
    if web_runner:
        logger.info("Shutting down Mini App server...")
        await web_runner.cleanup()


async def main():
    config.validate()
    logger.info(f"Starting {config.company_name} FinanceBot...")
    logger.info(f"Admins: {config.admin_ids}")

    # Bot instance (created first so it can be passed to the web server)
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # ── Start Mini App web server (if configured) ──
    web_runner = None
    if config.webapp_url:
        from webapp.server import start_webapp
        web_runner = await start_webapp(bot)
        logger.info(f"Mini App URL: {config.webapp_url}")
    else:
        logger.info("Mini App server not started (WEBAPP_URL not set). Run with ngrok to enable.")

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ── Middleware ──
    dp.update.middleware(DatabaseMiddleware())

    # ── Routers ──
    dp.include_router(setup_routers())
    
    # Store web_runner in dispatcher data for graceful shutdown
    dp.workflow_data["web_runner"] = web_runner

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
