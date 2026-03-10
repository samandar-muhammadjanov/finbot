"""
webapp/server.py — aiohttp REST API server for the Telegram Mini App.

Validates every request using Telegram initData HMAC so only
real Telegram users (admins) can call the API.

Runs on port 8080 (or WEBAPP_PORT) alongside the aiogram bot.
"""

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl, unquote

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.engine import get_session
from database.models.category import CategoryType
from bot.services import (
    get_full_stats,
    get_recent_transactions,
    get_categories,
    add_transaction,
    delete_transaction,
    add_category,
    deactivate_category,
    get_transaction_by_id,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Telegram initData validation
# ──────────────────────────────────────────────

def _validate_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram Web App initData using HMAC-SHA256.
    Returns parsed data dict on success, None on failure.
    """
    try:
        parsed = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData", config.bot_token.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None
        return parsed
    except Exception:
        return None


def _get_user_id(request: web.Request) -> int | None:
    """Extract and validate Telegram user ID from initData header."""
    init_data = request.headers.get("X-Init-Data", "")
    if not init_data:
        return None
    parsed = _validate_init_data(init_data)
    if not parsed:
        return None
    try:
        user = json.loads(parsed.get("user", "{}"))
        return int(user.get("id", 0)) or None
    except Exception:
        return None


def _require_admin(handler):
    """Decorator: reject non-admin callers with 403."""
    async def wrapper(request: web.Request):
        user_id = _get_user_id(request)
        if not user_id:
            logger.warning(f"Auth failed: user_id could not be extracted from initData. Header: {request.headers.get('X-Init-Data', '')[:20]}...")
            return web.json_response({"error": "Forbidden: Invalid initData"}, status=403)
        if user_id not in config.admin_ids:
            logger.warning(f"Auth failed: user_id {user_id} is not in config.admin_ids {config.admin_ids}")
            return web.json_response({"error": "Forbidden: Not an admin"}, status=403)
        return await handler(request)
    return wrapper


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def _cors(response: web.Response) -> web.Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Init-Data"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response


def json_ok(data) -> web.Response:
    return _cors(web.json_response(data))


def json_err(msg, status=400) -> web.Response:
    return _cors(web.json_response({"error": msg}, status=status))


async def options_handler(request: web.Request) -> web.Response:
    return _cors(web.Response(status=204))


# ──────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────

@_require_admin
async def get_stats(request: web.Request) -> web.Response:
    async with get_session() as session:
        stats = await get_full_stats(session)
        s = stats.all_time
        t = stats.today
        m = stats.this_month
        return json_ok({
            "all_time": {"income": s.total_income, "expense": s.total_expense, "balance": s.balance},
            "today":    {"income": t.total_income, "expense": t.total_expense, "balance": t.balance},
            "month":    {"income": m.total_income, "expense": m.total_expense, "balance": m.balance},
            "top_expense": [{"name": n, "amount": a} for n, a in stats.top_expense_categories],
            "top_income":  [{"name": n, "amount": a} for n, a in stats.top_income_categories],
        })


@_require_admin
async def get_transactions(request: web.Request) -> web.Response:
    page = int(request.rel_url.query.get("page", 0))
    per_page = 20
    async with get_session() as session:
        txs = await get_recent_transactions(session, limit=per_page, offset=page * per_page)
        all_txs = await get_recent_transactions(session, limit=9999)
        return json_ok({
            "total": len(all_txs),
            "page": page,
            "items": [
                {
                    "id": tx.id,
                    "type": tx.type.value,
                    "amount": tx.amount,
                    "category": tx.category_rel.name if tx.category_rel else "—",
                    "description": tx.description or "",
                    "date": tx.created_at.strftime("%d.%m.%Y %H:%M"),
                }
                for tx in txs
            ],
        })


@_require_admin
async def post_transaction(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        tx_type = CategoryType(body["type"])
        amount = float(body["amount"])
        category_id = int(body["category_id"])
        description = body.get("description") or None
        user_id = _get_user_id(request)
    except Exception as e:
        return json_err(f"Invalid body: {e}")

    async with get_session() as session:
        tx = await add_transaction(
            session=session,
            type_=tx_type,
            amount_dollars=amount,
            category_id=category_id,
            description=description,
            created_by=user_id,
        )
        tx = await get_transaction_by_id(session, tx.id)
        return json_ok({
            "id": tx.id,
            "type": tx.type.value,
            "amount": tx.amount,
            "category": tx.category_rel.name if tx.category_rel else "—",
        })


@_require_admin
async def delete_tx(request: web.Request) -> web.Response:
    tx_id = int(request.match_info["id"])
    async with get_session() as session:
        deleted = await delete_transaction(session, tx_id)
    if deleted:
        return json_ok({"deleted": tx_id})
    return json_err("Not found", status=404)


@_require_admin
async def get_cats(request: web.Request) -> web.Response:
    async with get_session() as session:
        cats = await get_categories(session)
    return json_ok([
        {"id": c.id, "name": c.name, "type": c.type.value} for c in cats
    ])


@_require_admin
async def post_category(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        name = body["name"].strip()
        cat_type = CategoryType(body["type"])
    except Exception as e:
        return json_err(f"Invalid body: {e}")

    async with get_session() as session:
        try:
            cat = await add_category(session, name=name, type_=cat_type)
            return json_ok({"id": cat.id, "name": cat.name, "type": cat.type.value})
        except ValueError as e:
            return json_err(str(e))


@_require_admin
async def delete_cat(request: web.Request) -> web.Response:
    cat_id = int(request.match_info["id"])
    async with get_session() as session:
        deleted = await deactivate_category(session, cat_id)
    if deleted:
        return json_ok({"deleted": cat_id})
    return json_err("Not found", status=404)


# ──────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()

    import pathlib
    webapp_dir = pathlib.Path(__file__).parent

    # Static files (index.html)
    app.router.add_get("/", lambda r: web.FileResponse(webapp_dir / "index.html"))

    # Preflight CORS
    app.router.add_route("OPTIONS", "/{path_info:.*}", options_handler)

    # API
    app.router.add_get("/api/stats",             get_stats)
    app.router.add_get("/api/transactions",      get_transactions)
    app.router.add_post("/api/transactions",     post_transaction)
    app.router.add_delete("/api/transactions/{id}", delete_tx)
    app.router.add_get("/api/categories",        get_cats)
    app.router.add_post("/api/categories",       post_category)
    app.router.add_delete("/api/categories/{id}", delete_cat)

    return app


async def start_webapp() -> web.AppRunner:
    """Start the aiohttp server (called from main.py)."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.webapp_port)
    await site.start()
    logger.info(f"Web App server running on http://0.0.0.0:{config.webapp_port}")
    return runner
