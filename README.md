# 💰 FinanceBot — Company Financial Management Telegram Bot

A production-ready Telegram bot for tracking company income and expenses, with real-time statistics, role-based access, and an inline admin panel.

---

## 🏗 Architecture Overview

```
finbot/
├── main.py                     # Entry point — bot startup & polling
├── config.py                   # Centralized config from .env
├── requirements.txt
├── .env.example
├── database/
│   ├── engine.py               # Async SQLAlchemy engine & session factory
│   ├── schema.sql              # Raw SQL schema (reference / manual setup)
│   └── models/
│       ├── base.py             # Declarative base
│       ├── user.py             # Telegram user table
│       ├── category.py         # Income/expense categories
│       └── transaction.py      # Core financial ledger
└── bot/
    ├── handlers/
    │   ├── common.py           # /start /help — all users
    │   ├── stats.py            # /stats /transactions — all users
    │   └── admin.py            # Admin panel, FSM flows, category mgmt
    ├── keyboards/
    │   └── main_keyboards.py   # All inline & reply keyboards
    ├── middlewares/
    │   ├── db_middleware.py    # Injects DB session + upserts user
    │   └── admin_middleware.py # @require_admin decorator
    ├── services/
    │   ├── user_service.py     # User CRUD
    │   ├── category_service.py # Category CRUD
    │   ├── transaction_service.py # Transaction CRUD
    │   └── stats_service.py    # Financial statistics queries
    └── utils/
        └── formatters.py       # Message formatting helpers
```

---

## 🗄 Database Schema

```sql
users        — Telegram user profiles + is_admin flag
categories   — Typed (income/expense) transaction buckets
transactions — Core financial ledger (soft-deleted, amount in cents)
```

All monetary values are stored as **integer cents** to avoid float precision issues.  
Transactions are **soft-deleted** (is_deleted flag) to preserve audit trail.

---

## ⚙️ Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### 2. Clone & install dependencies

```bash
git clone <repo>
cd finbot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=7123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/finbot
ADMIN_IDS=123456789,987654321   # Your Telegram user ID(s)
COMPANY_NAME=Acme Corp
```

> **How to find your Telegram user ID:** Message [@userinfobot](https://t.me/userinfobot)

### 4. Create the database

```bash
# Option A — let SQLAlchemy create tables automatically on startup
# (handled by init_db() in main.py)

# Option B — run the SQL schema manually
psql -U postgres -d finbot -f database/schema.sql
```

### 5. Run the bot

```bash
python main.py
```

---

## 👥 User Roles

| Feature                        | User | Admin |
|-------------------------------|------|-------|
| `/start` `/help`               | ✅   | ✅    |
| `/stats` — view statistics     | ✅   | ✅    |
| `/transactions` — view history | ✅   | ✅    |
| `/admin` — admin panel         | ❌   | ✅    |
| Add income / expense           | ❌   | ✅    |
| Delete transactions            | ❌   | ✅    |
| Manage categories              | ❌   | ✅    |

Admin IDs are set in `.env` — no database migration needed to add/remove admins.

---

## 📱 Bot Commands

### All Users
```
/start        — Welcome message + role-based menu
/help         — List available commands
/stats        — Full financial statistics
/transactions — Recent 10 transactions
```

### Admins Only
```
/admin         — Open admin panel (inline keyboard)
/add_income    — Start income transaction flow
/add_expense   — Start expense transaction flow
/del_tx <id>   — Delete transaction by ID
/categories    — Manage income/expense categories
```

---

## 📊 Statistics Output Example

```
📊 Acme Corp — Financial Stats

━━━━━━━━━━━━━━━━━━━━
🏦 All Time
  💰 Total Income:  $12,400.00
  💸 Total Expense: $7,300.00
  📈 Balance:       $5,100.00

📅 Today
  💰 Income:  $500.00
  💸 Expense: $120.00
  📈 Balance: $380.00

🗓 This Month
  💰 Income:  $3,200.00
  💸 Expense: $1,800.00
  📈 Balance: $1,400.00

🔴 Top Expense Categories
  1. Salaries: $4,000.00
  2. Rent: $1,500.00
  3. Software: $800.00

🟢 Top Income Categories
  1. Client Payment: $8,000.00
  2. Service Payment: $3,200.00
```

---

## 🔄 Admin Transaction Flow

```
Admin: /add_income (or taps button)
  ↓
Bot: Shows income categories as inline buttons
  ↓
Admin: Selects "Client Payment"
  ↓
Bot: "Enter the amount:"
  ↓
Admin: Types "1500"
  ↓
Bot: "Enter description or /skip"
  ↓
Admin: Types "Q1 project payment"
  ↓
Bot: ✅ Transaction #42 saved! $1,500.00 · Client Payment
```

---

## 🚀 Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Redis FSM Storage (recommended for production)

Replace `MemoryStorage` in `main.py`:

```python
from aiogram.fsm.storage.redis import RedisStorage
storage = RedisStorage.from_url("redis://localhost:6379")
```

### Webhook (instead of polling)

```python
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# In main():
await bot.set_webhook(f"https://yourdomain.com/webhook/{config.bot_token}")
app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=f"/webhook/{config.bot_token}")
setup_application(app, dp, bot=bot)
web.run_app(app, host="0.0.0.0", port=8080)
```

---

## 🛡 Security Notes

- Admin IDs are validated from `config.ADMIN_IDS` on every request — no DB lookup needed
- Transactions use soft-delete — full audit trail preserved
- Monetary amounts stored as integer cents — no float precision bugs
- All DB operations are async and use connection pooling
- FSM state is per-user — concurrent admin sessions don't interfere
