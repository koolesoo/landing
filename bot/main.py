"""Telegram-бот: гайд с сайта и запись на услуги."""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from guide_content import (
    BOOKING_INTRO,
    BOOKING_SUCCESS,
    GUIDE_CAPTION,
    GUIDE_FILE,
    GUIDE_FILENAME,
    GUIDE_TITLE,
    WELCOME_DEFAULT,
    WELCOME_FROM_SITE,
)
from services import EXPERTS, get_expert, get_tariff

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
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "koolesoo").strip().lstrip("@").lower()
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

ptb_app: Application | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS booking_starts (
                telegram_user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                expert_id TEXT NOT NULL,
                tariff_id TEXT NOT NULL,
                expert_name TEXT NOT NULL,
                tariff_title TEXT NOT NULL,
                tariff_price TEXT NOT NULL,
                created_at TEXT NOT NULL
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
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
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
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception("Failed to notify admin (chat_id=%s)", chat_id)


def mark_booking_start(user_id: int, username: str | None, full_name: str | None) -> bool:
    """Возвращает True, если это первый старт записи у пользователя."""
    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT 1 FROM booking_starts WHERE telegram_user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            return False
        conn.execute(
            """
            INSERT INTO booking_starts (telegram_user_id, username, full_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, full_name, utc_now()),
        )
        return True


def save_booking(
    user_id: int,
    username: str | None,
    full_name: str | None,
    expert_id: str,
    tariff_id: str,
    expert_name: str,
    tariff_title: str,
    tariff_price: str,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO bookings (
                telegram_user_id, username, full_name,
                expert_id, tariff_id, expert_name, tariff_title, tariff_price, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                full_name,
                expert_id,
                tariff_id,
                expert_name,
                tariff_title,
                tariff_price,
                utc_now(),
            ),
        )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📘 Получить гайд", callback_data="menu:guide")],
            [InlineKeyboardButton("🗓️ Записаться на услугу", callback_data="book:start")],
        ]
    )


def experts_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(expert.name, callback_data=f"book:expert:{expert.id}")]
        for expert in EXPERTS.values()
    ]
    rows.append([InlineKeyboardButton("« Назад", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def tariffs_keyboard(expert_id: str) -> InlineKeyboardMarkup:
    expert = get_expert(expert_id)
    if not expert:
        return experts_keyboard()
    rows = [
        [
            InlineKeyboardButton(
                f"{tariff.title} · {tariff.price}",
                callback_data=f"book:tariff:{expert.id}:{tariff.id}",
            )
        ]
        for tariff in expert.tariffs
    ]
    rows.append([InlineKeyboardButton("« К экспертам", callback_data="book:start")])
    return InlineKeyboardMarkup(rows)


def confirm_keyboard(expert_id: str, tariff_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить запись",
                    callback_data=f"book:confirm:{expert_id}:{tariff_id}",
                )
            ],
            [InlineKeyboardButton("« К тарифам", callback_data=f"book:expert:{expert_id}")],
        ]
    )


def after_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📘 Получить гайд", callback_data="menu:guide")],
            [InlineKeyboardButton("🗓️ Ещё одна запись", callback_data="book:start")],
        ]
    )


async def clear_message_buttons(query) -> None:
    """Убирает кнопки у сообщения, текст/файл оставляет — история не затирается."""
    if not query or not query.message:
        return
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.debug("Could not clear reply markup", exc_info=True)


async def send_ui_message(
    update: Update,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
    edit: bool = False,
) -> None:
    """edit=True — только внутри шагов записи; иначе новое сообщение (история сохраняется)."""
    query = update.callback_query
    message = update.effective_message
    if not message:
        return

    if edit and query and query.message and query.message.text is not None:
        try:
            await query.edit_message_text(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("Falling back to new message", exc_info=True)

    if query:
        await clear_message_buttons(query)

    await message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)


async def send_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    register_admin_chat_id(user.id, user.username)

    if update.callback_query:
        await clear_message_buttons(update.callback_query)

    if not GUIDE_FILE.is_file():
        await message.reply_text("Гайд временно недоступен. Напишите /book для записи.")
        logger.error("Guide file missing: %s", GUIDE_FILE)
        return

    with GUIDE_FILE.open("rb") as guide_file:
        await message.reply_document(
            document=guide_file,
            filename=GUIDE_FILENAME,
            caption=f"<b>{GUIDE_TITLE}</b>\n\n{GUIDE_CAPTION}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🗓️ Записаться на услугу", callback_data="book:start")]]
            ),
        )

    user_ref = format_user_ref(user.username, user.id, user.full_name)
    await notify_admin(
        context.bot,
        f"📘 <b>Гайд отправлен</b>\n{user_ref}",
    )


async def start_booking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    expert_id: str | None = None,
    edit: bool = False,
) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    register_admin_chat_id(user.id, user.username)

    is_first = mark_booking_start(user.id, user.username, user.full_name)
    if is_first:
        user_ref = format_user_ref(user.username, user.id, user.full_name)
        await notify_admin(
            context.bot,
            f"🟡 <b>Старт записи</b>\n{user_ref}\nНачал оформление заявки.",
        )

    if expert_id and get_expert(expert_id):
        await show_tariffs(update, expert_id, edit=edit)
        return

    await send_ui_message(
        update,
        BOOKING_INTRO,
        reply_markup=experts_keyboard(),
        edit=edit,
    )


async def show_tariffs(update: Update, expert_id: str, *, edit: bool = False) -> None:
    expert = get_expert(expert_id)
    if not expert:
        return

    await send_ui_message(
        update,
        f"Эксперт: <b>{expert.name}</b>\n\nВыберите тариф:",
        reply_markup=tariffs_keyboard(expert_id),
        parse_mode=ParseMode.HTML,
        edit=edit,
    )


async def show_confirm(update: Update, expert_id: str, tariff_id: str) -> None:
    expert = get_expert(expert_id)
    tariff = get_tariff(expert_id, tariff_id)
    if not expert or not tariff:
        return

    meta = f"\n{tariff.meta}" if tariff.meta else ""
    text = (
        f"Проверьте заявку:\n\n"
        f"👤 <b>{expert.name}</b>\n"
        f"📦 {tariff.title}\n"
        f"💰 {tariff.price}{meta}"
    )
    await send_ui_message(
        update,
        text,
        reply_markup=confirm_keyboard(expert_id, tariff_id),
        parse_mode=ParseMode.HTML,
        edit=True,
    )


async def complete_booking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    expert_id: str,
    tariff_id: str,
) -> None:
    query = update.callback_query
    user = update.effective_user
    expert = get_expert(expert_id)
    tariff = get_tariff(expert_id, tariff_id)
    if not query or not user or not expert or not tariff:
        return

    save_booking(
        user.id,
        user.username,
        user.full_name,
        expert.id,
        tariff.id,
        expert.name,
        tariff.title,
        tariff.price,
    )

    success_text = (
        BOOKING_SUCCESS
        + f"\n\n👤 {expert.name}\n📦 {tariff.title}\n💰 {tariff.price}"
    )
    # Финальный success — отдельным сообщением, черновик заявки оставляем в истории
    await clear_message_buttons(query)
    await query.message.reply_text(
        success_text,
        parse_mode=ParseMode.HTML,
        reply_markup=after_success_keyboard(),
    )

    user_ref = format_user_ref(user.username, user.id, user.full_name)
    await notify_admin(
        context.bot,
        (
            f"🟢 <b>Успешная запись</b>\n"
            f"{user_ref}\n"
            f"Эксперт: {expert.name}\n"
            f"Тариф: {tariff.title} · {tariff.price}"
        ),
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    register_admin_chat_id(user.id, user.username)

    args = context.args or []
    payload = args[0].lower() if args else ""

    if payload.startswith("guide"):
        await message.reply_text(WELCOME_FROM_SITE)
        await send_guide(update, context)
        return

    if payload.startswith("book_"):
        expert_id = payload.replace("book_", "", 1)
        await start_booking(update, context, expert_id=expert_id if expert_id in EXPERTS else None)
        return

    if payload.startswith("book"):
        await start_booking(update, context)
        return

    await message.reply_text(WELCOME_DEFAULT, reply_markup=main_menu_keyboard())


async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_guide(update, context)


async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_booking(update, context)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data
    user = update.effective_user
    if user:
        register_admin_chat_id(user.id, user.username)

    # Меню / гайд / новая запись — всегда новые сообщения, чтобы не затирать success
    if data == "menu:home":
        await send_ui_message(
            update,
            WELCOME_DEFAULT,
            reply_markup=main_menu_keyboard(),
            edit=False,
        )
        return

    if data == "menu:guide":
        await send_guide(update, context)
        return

    if data == "book:start":
        await start_booking(update, context, edit=False)
        return

    if data.startswith("book:expert:"):
        expert_id = data.split(":", 2)[2]
        await show_tariffs(update, expert_id, edit=True)
        return

    if data.startswith("book:tariff:"):
        _, _, expert_id, tariff_id = data.split(":", 3)
        await show_confirm(update, expert_id, tariff_id)
        return

    if data.startswith("book:confirm:"):
        _, _, expert_id, tariff_id = data.split(":", 3)
        await complete_booking(update, context, expert_id, tariff_id)
        return


def build_ptb_app() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("guide", guide_command))
    application.add_handler(CommandHandler("book", book_command))
    application.add_handler(CallbackQueryHandler(on_callback))
    return application


def cors_headers(request: web.Request) -> dict[str, str]:
    origin = request.headers.get("Origin", "")
    headers: dict[str, str] = {}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return headers


async def health_handler(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


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
    app.router.add_post("/telegram/{secret}", telegram_webhook_handler)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_shutdown)
    return app


def main() -> None:
    web.run_app(create_web_app(), host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
