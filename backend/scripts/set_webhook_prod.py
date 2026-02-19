#!/usr/bin/env python3
"""
Simple script to set Telegram Webhook without loading the full app config.
"""
import httpx
import sys

# Replace these values as needed
TELEGRAM_BOT_TOKEN = "8373208403:AAHVVb7dEC6DOh2xJOSMTzdhONRtyL2q8EU"
TELEGRAM_WEBHOOK_SECRET = "4c931af77b7ffcc5f0f970c10f6680bca9d827d3c195721725f38b96e2437ac9"
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
