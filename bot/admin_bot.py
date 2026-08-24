"""Отдельный админ-бот для уведомлений о событиях основного бота."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from telegram_client import build_application, telegram_proxy_url

logger = logging.getLogger("admin-bot")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "guide.db"

admin_app: Application | None = None


def admin_bot_token() -> str:
    return os.getenv("ADMIN_BOT_TOKEN", "").strip()


def admin_bot_username() -> str:
    return os.getenv("ADMIN_BOT_USERNAME", "career67_bot").strip().lstrip("@")


def allowed_admin_usernames() -> set[str]:
    raw = os.getenv("ALLOWED_ADMIN_USERNAMES", "").strip()
    value = raw if raw else "neradana,koolesoo"
    return {
        username.strip().lstrip("@").lower()
        for username in value.split(",")
        if username.strip()
    }


def _ensure_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def _set_setting(key: str, value: str) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        _ensure_settings_table(conn)
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def register_admin_chat_id(username: str, chat_id: int) -> None:
    _set_setting(f"admin_chat:{username.lower()}", str(chat_id))
    logger.info("Admin chat registered: @%s -> %s", username, chat_id)


def get_admin_chat_ids() -> list[int]:
    chat_ids: list[int] = []

    env_ids = os.getenv("ADMIN_CHAT_IDS", "").strip()
    if env_ids:
        for part in env_ids.split(","):
            part = part.strip()
            if part.isdigit():
                chat_ids.append(int(part))

    if DB_PATH.is_file():
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT value FROM settings WHERE key LIKE 'admin_chat:%'"
            ).fetchall()
            legacy = conn.execute(
                "SELECT value FROM settings WHERE key = 'admin_chat_id'"
            ).fetchone()

        for (value,) in rows:
            if value.isdigit():
                chat_ids.append(int(value))

        if legacy and legacy[0].isdigit():
            chat_ids.append(int(legacy[0]))

    seen: set[int] = set()
    unique: list[int] = []
    for chat_id in chat_ids:
        if chat_id not in seen:
            seen.add(chat_id)
            unique.append(chat_id)
    return unique


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    if not user.username:
        await message.reply_text(
            "Доступ только для аккаунтов с публичным username в Telegram."
        )
        return

    username = user.username.lower()
    allowed = allowed_admin_usernames()
    if username not in allowed:
        await message.reply_text("⛔ Нет доступа к этому боту.")
        logger.warning(
            "Unauthorized admin bot access: @%s (id=%s)",
            username,
            user.id,
        )
        return

    register_admin_chat_id(username, user.id)
    await message.reply_text(
        "✅ Уведомления подключены.\n"
        "Сюда будут приходить события с основного бота.\n\n"
        f"Аккаунт: @{username}"
    )


async def notify_admins(text: str) -> None:
    token = admin_bot_token()
    if not token:
        logger.warning("ADMIN_BOT_TOKEN is not set – admin notifications disabled")
        return

    chat_ids = get_admin_chat_ids()
    if not chat_ids:
        allowed = ", ".join(f"@{name}" for name in sorted(allowed_admin_usernames()))
        logger.warning(
            "No admin chat ids – %s should /start @%s once",
            allowed,
            admin_bot_username(),
        )
        return

    async def _send(bot: Bot) -> None:
        for chat_id in chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                logger.info("Admin notification sent to chat_id=%s", chat_id)
            except Exception:
                logger.exception("Failed to notify admin (chat_id=%s)", chat_id)

    if admin_app and admin_app.bot:
        await _send(admin_app.bot)
        return

    proxy = telegram_proxy_url() or None
    async with Bot(token, proxy=proxy) as bot:
        await _send(bot)


def build_admin_app() -> Application | None:
    token = admin_bot_token()
    if not token:
        logger.warning("ADMIN_BOT_TOKEN is not set – admin notifications disabled")
        return None

    application = build_application(token)
    application.add_handler(CommandHandler("start", admin_start))
    return application
