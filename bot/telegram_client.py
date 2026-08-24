"""Общая сборка Telegram Application с опциональным прокси."""

from __future__ import annotations

import os

from telegram.ext import Application


def telegram_proxy_url() -> str:
    return os.getenv("TELEGRAM_PROXY", "").strip()


def build_application(token: str) -> Application:
    builder = Application.builder().token(token)
    proxy = telegram_proxy_url()
    if proxy:
        builder = builder.proxy(proxy).get_updates_proxy(proxy)
    return builder.build()
