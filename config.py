"""
config.py — Centralized configuration loader.
Reads environment variables from .env and exposes a typed Config object.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Telegram
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    bot_name: str = field(default_factory=lambda: os.getenv("BOT_NAME", "FinanceBot"))
    company_name: str = field(default_factory=lambda: os.getenv("COMPANY_NAME", "Company"))

    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/finbot"
        )
    )

    # Admins — stored as Telegram user IDs
    admin_ids: List[int] = field(
        default_factory=lambda: [
            int(x.strip())
            for x in os.getenv("ADMIN_IDS", "").split(",")
            if x.strip().isdigit()
        ]
    )

    # Mini App
    webapp_url: str = field(default_factory=lambda: os.getenv("WEBAPP_URL", ""))
    webapp_port: int = field(default_factory=lambda: int(os.getenv("WEBAPP_PORT", "8080")))


    def validate(self):
        """Raise early if required config is missing."""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is not set in environment variables.")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not set in environment variables.")


# Singleton — import this everywhere
config = Config()
