#!/usr/bin/env python3
import argparse
import logging
import os
import sys

# Ensure backend root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.workers.email_tasks import _send_email, _mailgun_configured, _smtp_configured
from app.services.telegram_service import TelegramService

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("check_notifications")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

def check_email(target_email):
    print(f"\n📧 Checking Email Configuration for {target_email}")
    is_mailgun = _mailgun_configured()
    is_smtp = _smtp_configured()

    if is_mailgun:
        print("✅ Mailgun is configured.")
    elif is_smtp:
        print("✅ SMTP is configured.")
    else:
        print("❌ No email provider configured (Mailgun or SMTP).")
        print("   Please check your .env file for MAILGUN or SMTP settings.")
        return

    print("   Sending test email...")
    try:
        success = _send_email(
            to_email=target_email,
            subject="Test Notification from Kabul Sweets Script",
            html_body=(
                "<div style='font-family: sans-serif; padding: 20px; text-align: center; border: 1px solid #ddd;'>"
                "<h1 style='color: #27ae60;'>It Works!</h1>"
                "<p>This is a test notification from the <code>check_notifications.py</code> script.</p>"
                "<p>If you see this, your email configuration is correct.</p>"
                "</div>"
            )
        )
        if success:
            print(f"✅ Test email successfully sent to {target_email}")
        else:
            print("⚠️ Email function returned False. Check application logs for details.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def check_telegram():
    print("\n📱 Checking Telegram Configuration")
    try:
        telegram = TelegramService()
        if not telegram.is_configured():
            print("❌ Telegram is not configured.")
            print("   Check TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_IDS in .env")
            return

        print(f"✅ Telegram is configured.")
        print(f"   Bot Token (last 5): ...{telegram.bot_token[-5:]}")
        print(f"   Admin Chat IDs: {telegram.admin_chat_ids}")

        print("   Sending test message to all admin chats...")
        for chat_id in telegram.admin_chat_ids:
            try:
                ok = telegram.send_text(
                    chat_id,
                    "🔔 <b>Test Notification</b>\nThis message confirms your Telegram bot is working correctly.",
                )
                if ok:
                    print(f"✅ Sent test message to chat_id: {chat_id}")
                else:
                    print(f"❌ Telegram rejected test message for chat_id: {chat_id}. Check bot token/webhook config.")
            except Exception as e:
                print(f"❌ Failed to send to {chat_id}: {e}")

    except Exception as e:
        print(f"❌ Telegram check failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check notification configurations")
    parser.add_argument("--email", help="Target email address for test email")
    args = parser.parse_args()

    if args.email:
        check_email(args.email)
    else:
        print("ℹ️  No email provided. Skipping email check. Use --email <address> to test email.")
    
    check_telegram()
