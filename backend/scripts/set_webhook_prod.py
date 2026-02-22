#!/usr/bin/env python3
"""
Simple script to set Telegram Webhook without loading the full app config.
"""
import httpx
import sys

import os

# Secrets must be environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
BACKEND_URL = "https://api.kabulsweets.com"

def set_webhook():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_WEBHOOK_SECRET:
        print("❌ TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET must be set.")
        sys.exit(1)

    webhook_url = f"{BACKEND_URL}/api/v1/telegram/webhook"
    print(f"Setting webhook to: {webhook_url}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    try:
        response = httpx.post(
            url,
            data={
                "url": webhook_url,
                "secret_token": TELEGRAM_WEBHOOK_SECRET,
                "drop_pending_updates": "true",
                # Force callback updates so inline keyboard buttons always work.
                "allowed_updates": '["message","callback_query"]',
            },
        )
        response.raise_for_status()
        print("✅ Success:", response.json())
    except Exception as e:
        print("❌ Error:", e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BACKEND_URL = sys.argv[1].rstrip("/")
    set_webhook()
