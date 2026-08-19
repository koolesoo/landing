"""Telegram-бот: отправляет гайд пользователям, пришедшим с сайта."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from guide_content import (
    GUIDE_PARTS,
    GUIDE_TITLE,
    WELCOME_DEFAULT,
    WELCOME_FROM_SITE,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("guide-bot")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "guide.db"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "neradana").strip().lstrip("@").lower()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
BOT_MODE = os.getenv("BOT_MODE", "polling").strip().lower()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me").strip()
PORT = int(os.getenv("PORT", "8080"))
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://koolesoo.github.io,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
}

TELEGRAM_USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{3,31}$")

ptb_app: Application | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_username(value: str) -> str | None:
    username = value.strip().lstrip("@")
    if not TELEGRAM_USERNAME_RE.fullmatch(username):
        return None
    return username.lower()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guide_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                delivered_at TEXT,
                telegram_user_id INTEGER,
                source TEXT NOT NULL DEFAULT 'site'
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_guide_requests_username
            ON guide_requests (telegram_username)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )


def get_setting(key: str) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None


def set_setting(key: str, value: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_admin_chat_id() -> int | None:
    if ADMIN_CHAT_ID:
        return int(ADMIN_CHAT_ID)
    stored = get_setting("admin_chat_id")
    return int(stored) if stored else None


def register_admin_chat_id(user_id: int, username: str | None) -> None:
    if username and username.lower() == ADMIN_USERNAME:
        set_setting("admin_chat_id", str(user_id))
        logger.info("Admin chat id registered: %s (@%s)", user_id, username)


def format_user_ref(username: str | None, user_id: int | None = None, full_name: str | None = None) -> str:
    parts: list[str] = []
    if full_name:
        parts.append(full_name)
    if username:
        parts.append(f"@{username}")
    elif user_id:
        parts.append(f"id:{user_id}")
    return " · ".join(parts) if parts else "неизвестный пользователь"


async def notify_admin(bot, text: str) -> None:
    chat_id = get_admin_chat_id()
    if not chat_id:
        logger.warning("Admin chat id is not set — @%s should /start the bot once", ADMIN_USERNAME)
        return
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        logger.exception("Failed to notify admin (chat_id=%s)", chat_id)


def save_guide_request(username: str, source: str = "site") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO guide_requests (telegram_username, created_at, source)
            VALUES (?, ?, ?)
            """,
            (username, utc_now(), source),
        )


def mark_delivered(user_id: int, username: str | None) -> None:
    if not username:
        return
    delivered_at = utc_now()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE guide_requests
            SET delivered_at = ?, telegram_user_id = ?
            WHERE telegram_username = ? AND delivered_at IS NULL
            """,
            (delivered_at, user_id, username.lower()),
        )


async def send_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    register_admin_chat_id(user.id, user.username)

    await message.reply_text(f"<b>{GUIDE_TITLE}</b>", parse_mode=ParseMode.HTML)
    for part in GUIDE_PARTS:
        await message.reply_text(part, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    username = user.username.lower() if user.username else None
    mark_delivered(user.id, username)
    logger.info("Guide delivered to user_id=%s username=%s", user.id, username)

    user_ref = format_user_ref(user.username, user.id, user.full_name)
    await notify_admin(
        context.bot,
        f"📘 <b>Запрос гайда в боте</b>\n{user_ref}\nГайд отправлен.",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    register_admin_chat_id(user.id, user.username)

    args = context.args or []
    from_site = bool(args) and args[0].startswith("guide")

    if from_site:
        await message.reply_text(WELCOME_FROM_SITE)
    else:
        await message.reply_text(WELCOME_DEFAULT)

    await send_guide(update, context)


async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_guide(update, context)


def build_ptb_app() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("guide", guide_command))
    return application


def bot_deep_link() -> str:
    if not BOT_USERNAME:
        return ""
    return f"https://t.me/{BOT_USERNAME}?start=guide"


def cors_headers(request: web.Request) -> dict[str, str]:
    origin = request.headers.get("Origin", "")
    headers: dict[str, str] = {}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return headers


async def health_handler(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def guide_handler(request: web.Request) -> web.Response:
    headers = cors_headers(request)

    if request.method == "OPTIONS":
        return web.Response(
            status=204,
            headers={
                **headers,
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"detail": "invalid_json"}, status=400, headers=headers)

    if not payload.get("consent"):
        return web.json_response({"detail": "consent_required"}, status=400, headers=headers)

    username = normalize_username(str(payload.get("telegram", "")))
    if not username:
        return web.json_response({"detail": "invalid_telegram_username"}, status=400, headers=headers)

    link = bot_deep_link()
    if not link:
        return web.json_response({"detail": "bot_not_configured"}, status=503, headers=headers)

    save_guide_request(username, source="site")
    logger.info("Guide request from site: @%s", username)

    if ptb_app is not None:
        await notify_admin(
            ptb_app.bot,
            f"📝 <b>Заявка на гайд с сайта</b>\n@{username}\nЖдёт перехода в бота и Start.",
        )

    return web.json_response(
        {
            "ok": True,
            "bot_url": link,
            "message": "Откройте бота в Telegram и нажмите «Start» — гайд придёт автоматически.",
        },
        headers=headers,
    )


async def telegram_webhook_handler(request: web.Request) -> web.Response:
    if request.match_info.get("secret") != WEBHOOK_SECRET:
        raise web.HTTPNotFound()
    if ptb_app is None:
        raise web.HTTPServiceUnavailable(text="bot_not_ready")

    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return web.json_response({"ok": True})


async def on_startup(app: web.Application) -> None:
    global ptb_app

    init_db()
    ptb_app = build_ptb_app()
    await ptb_app.initialize()
    await ptb_app.start()

    if BOT_MODE == "webhook":
        if not WEBHOOK_URL:
            raise RuntimeError("WEBHOOK_URL is required when BOT_MODE=webhook")
        webhook_url = f"{WEBHOOK_URL}/telegram/{WEBHOOK_SECRET}"
        await ptb_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info("Webhook set: %s", webhook_url)
    else:
        await ptb_app.bot.delete_webhook(drop_pending_updates=True)
        await ptb_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Polling started for @%s", BOT_USERNAME)


async def on_shutdown(app: web.Application) -> None:
    global ptb_app
    if ptb_app is None:
        return

    if BOT_MODE == "webhook":
        await ptb_app.bot.delete_webhook(drop_pending_updates=True)
    else:
        await ptb_app.updater.stop()

    await ptb_app.stop()
    await ptb_app.shutdown()
    ptb_app = None


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_route("*", "/api/guide", guide_handler)
    app.router.add_post("/telegram/{secret}", telegram_webhook_handler)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_shutdown)
    return app


def main() -> None:
    web.run_app(create_web_app(), host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
