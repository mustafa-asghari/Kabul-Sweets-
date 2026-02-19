#!/usr/bin/env python3
"""
Simple script to set Telegram Webhook without loading the full app config.
"""
import httpx
import sys

import os

# Secrets should be environment variables, not hardcoded
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or "8373208403:CHANGE_ME"
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip() or "CHANGE_ME"
BACKEND_URL = "https://api.kabulsweets.com"

def set_webhook():
    webhook_url = f"{BACKEND_URL}/api/v1/telegram/webhook/{TELEGRAM_WEBHOOK_SECRET}"
    print(f"Setting webhook to: {webhook_url}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    try:
        response = httpx.post(url, data={"url": webhook_url})
        response.raise_for_status()
        print("✅ Success:", response.json())
    except Exception as e:
        print("❌ Error:", e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BACKEND_URL = sys.argv[1].rstrip("/")
    set_webhook()
