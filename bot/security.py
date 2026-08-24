"""HTTP hardening: rate limits, probe blocking, security headers."""

from __future__ import annotations

import re
import time
from collections import defaultdict

from aiohttp import web

MAX_BODY_BYTES = 256 * 1024
RATE_LIMIT_WINDOW_SEC = 60.0
GENERAL_RATE_LIMIT = 120
WEBHOOK_RATE_LIMIT = 40

WEAK_WEBHOOK_SECRETS = frozenset(
    {
        "",
        "change-me",
        "change-me-to-random-string",
        "secret",
        "webhook",
    }
)

BLOCKED_PATH_RE = re.compile(
    r"^/(\.env|\.git|wp-|admin|phpmyadmin|\.aws|config\.|backup|dump\.sql|\.vscode|\.cursor)",
    re.IGNORECASE,
)


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_sec: float) -> None:
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_sec
        hits = [stamp for stamp in self._hits[key] if stamp > cutoff]
        if len(hits) >= self.max_requests:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


_general_limiter = SlidingWindowRateLimiter(GENERAL_RATE_LIMIT, RATE_LIMIT_WINDOW_SEC)
_webhook_limiter = SlidingWindowRateLimiter(WEBHOOK_RATE_LIMIT, RATE_LIMIT_WINDOW_SEC)


def validate_webhook_secret(bot_mode: str, webhook_secret: str) -> None:
    if bot_mode != "webhook":
        return
    if webhook_secret in WEAK_WEBHOOK_SECRETS or len(webhook_secret) < 24:
        raise RuntimeError(
            "WEBHOOK_SECRET must be a random string at least 24 characters long"
        )


def client_ip(request: web.Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.remote:
        return request.remote
    return "unknown"


def apply_security_headers(response: web.StreamResponse) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=(), payment=()",
    )
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.pop("Server", None)


@web.middleware
async def security_middleware(
    request: web.Request, handler: web.RequestHandler
) -> web.StreamResponse:
    path = request.path
    if BLOCKED_PATH_RE.search(path):
        raise web.HTTPNotFound()

    limiter = _webhook_limiter if path.startswith("/telegram/") else _general_limiter
    if not limiter.allow(client_ip(request)):
        raise web.HTTPTooManyRequests(text="rate_limit")

    if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
        raise web.HTTPRequestEntityTooLarge()

    try:
        response = await handler(request)
    except web.HTTPException as exc:
        apply_security_headers(exc)
        raise

    apply_security_headers(response)
    return response


async def catch_all_handler(_request: web.Request) -> web.Response:
    raise web.HTTPNotFound()
