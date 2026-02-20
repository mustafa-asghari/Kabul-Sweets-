# Notification System Setup Guide

This guide explains how to configure Email and Telegram notifications for Kabul Sweets in production (Railway).

## 1. Quick Diagnostics

We have included a diagnostics script to verify your configuration.
Run this from the `backend/` directory:

```bash
# Check configuration only
python3 scripts/check_notifications.py

# Send a test email
python3 scripts/check_notifications.py --email your-email@example.com

# Send a test Telegram alert
python3 scripts/check_notifications.py --telegram
```

If any of these fail, check the environment variables below.

---

## 2. Environment Variables

You must set these variables in your Railway project settings.

### Telegram Alerts (Admin)

1. **Create a Bot**: Message `@BotFather` on Telegram to create a new bot and get the token.
2. **Get Chat IDs**: Message `@userinfobot` (or your new bot if you set it up to echo) to get your Chat ID.

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | The token from BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_ADMIN_CHAT_IDS` | Comma-separated list of admin Chat IDs | `12345678, 98765432` |

### Email Sending (Mailgun - Recommended)

If you are using Mailgun (preferred for reliability):

| Variable | Description | Example |
|----------|-------------|---------|
| `MAILGUN_API_KEY` | Private API Key from Mailgun | `key-1234567890abcdef...` |
| `MAILGUN_DOMAIN` | Your verified domain | `mg.kabulsweets.com.au` |
| `MAILGUN_FROM_EMAIL` | Sender address | `orders@kabulsweets.com.au` |

### Email Sending (SMTP - Fallback)

If you are using Gmail or another SMTP provider:

| Variable | Description | Example (Gmail) |
|----------|-------------|-----------------|
| `SMTP_HOST` | SMTP Server Host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP Port | `587` |
| `SMTP_USER` | SMTP Username | `kabul.sweets.orders@gmail.com` |
| `SMTP_PASSWORD` | App Password (not login password) | `abcd efgh ijkl mnop` |
| `SMTP_FROM_EMAIL` | Sender address | `kabul.sweets.orders@gmail.com` |

> **Note:** If `MAILGUN_API_KEY` is set, the system will try Mailgun first. It does NOT automatically fallback to SMTP if Mailgun fails with an error (to prevent duplicate sending attempts on transient errors). Remove Mailgun vars to force SMTP usage.

---

## 3. Stripe & Webhooks

For automatic payment confirmation emails to work, Stripe webhooks must be configured.

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Production Secret Key (`sk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | Webhook Secret (`whsec_...`) |

1. Go to Stripe Dashboard > Developers > Webhooks.
2. Add endpoint: `https://your-backend-url.up.railway.app/api/v1/stripe/webhook`
3. Select events: `payment_intent.succeeded`.

## 4. Troubleshooting

*   **"Order notifications Failures"**:
    *   Check `TELEGRAM_ADMIN_CHAT_IDS`. It must be a list of integers. The system handles strings like `"123, 456"` automatically.
    *   Ensure the bot has been started interaction with the admin (click "Start" in the bot chat). Bots cannot initiate conversations with users who haven't started them.

*   **"400 Bad Request" on Approval**:
    *   This is often due to Stripe errors. Check the logs. We have added error handling to prevent the entire request from failing, but the payment link might not be generated if keys are wrong.

*   **Logo Errors**:
    *   We have added a safety check for the logo. Ensure `logo-no-background.png` exists in `admin_frontend/public/` if you are hosting the admin panel separately.
