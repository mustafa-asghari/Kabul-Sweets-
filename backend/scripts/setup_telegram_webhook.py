#!/usr/bin/env python3
"""
Script to set the Telegram webhook URL for the bot.
Run this script locally or in production to register your backend URL with Telegram.

Usage:
    python3 scripts/setup_telegram_webhook.py <YOUR_BACKEND_URL>

Example:
    python3 scripts/setup_telegram_webhook.py https://kabul-sweets-backend.up.railway.app
"""

import argparse
import os
import sys

import httpx

# Ensure backend/ is in python path
sys.path.append(os.getcwd())

from app.core.config import get_settings

def set_webhook(backend_url: str):
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN.strip()
    secret = settings.TELEGRAM_WEBHOOK_SECRET.strip()
    
    if not token or not secret:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_SECRET is not set in environment.")
        sys.exit(1)
        
    # Standardize backend URL (remove trailing slash)
    base_url = backend_url.rstrip("/")
    # Use Telegram secret header token instead of exposing secret in URL.
    webhook_url = f"{base_url}/api/v1/telegram/webhook"
    
    print(f"Setting webhook URL to: {webhook_url}")
    
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"
    
    try:
        response = httpx.post(
            api_url,
            data={
                "url": webhook_url,
                "secret_token": secret,
                "drop_pending_updates": "true",
            },
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook set successfully!")
            print(f"Response: {result}")
        else:
            print("❌ Failed to set webhook.")
            print(f"Response: {result}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Set Telegram Webhook URL")
    parser.add_argument("url", help="The public HTTPS URL of your backend (e.g. https://myapp.railway.app)")
    args = parser.parse_args()
    
    set_webhook(args.url)

if __name__ == "__main__":
    main()
