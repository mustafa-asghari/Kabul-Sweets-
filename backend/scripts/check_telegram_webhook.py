#!/usr/bin/env python3
"""
Inspect Telegram webhook registration and delivery status.

Usage:
    python3 scripts/check_telegram_webhook.py
"""

import sys
import os
from datetime import datetime, timezone

import httpx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.core.config import get_settings


def _fmt_unix_ts(value: int | None) -> str:
    if not value:
        return "N/A"
    try:
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return str(value)


def main() -> int:
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN.strip()
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN is not set.")
        return 1

    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    try:
        response = httpx.get(url, timeout=20.0)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code if exc.response is not None else "unknown"
        print(f"❌ Failed to fetch webhook info: Telegram API returned HTTP {code}.")
        return 1
    except Exception as exc:
        print(f"❌ Failed to fetch webhook info: {exc}")
        return 1

    if not payload.get("ok"):
        print(f"❌ Telegram API returned error: {payload}")
        return 1

    info = payload.get("result", {}) or {}
    print("✅ Telegram webhook info")
    print(f"   URL: {info.get('url') or '(not set)'}")
    print(f"   Pending updates: {info.get('pending_update_count', 0)}")
    print(f"   Last error date (UTC): {_fmt_unix_ts(info.get('last_error_date'))}")
    print(f"   Last error message: {info.get('last_error_message') or 'None'}")
    print(f"   Last sync error date (UTC): {_fmt_unix_ts(info.get('last_synchronization_error_date'))}")
    print(f"   Max connections: {info.get('max_connections', 'N/A')}")
    print(f"   IP address: {info.get('ip_address') or 'N/A'}")
    print(f"   Has custom cert: {info.get('has_custom_certificate', False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
