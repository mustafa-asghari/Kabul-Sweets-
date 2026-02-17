"""
Email background tasks.
Handles order confirmations, receipts, and notifications.
Uses Mailgun API when configured, with SMTP fallback.
"""

import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

import httpx

from app.celery_app import celery_app

logger = logging.getLogger("app.workers.email")

# Mailgun config from environment (preferred provider)
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "").strip()
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "").strip()
MAILGUN_BASE_URL = os.getenv("MAILGUN_BASE_URL", "https://api.mailgun.net").rstrip("/")
MAILGUN_FROM_EMAIL = os.getenv("MAILGUN_FROM_EMAIL", "").strip()
MAILGUN_FROM_NAME = os.getenv("MAILGUN_FROM_NAME", "").strip()
try:
    MAILGUN_TIMEOUT_SECONDS = float(os.getenv("MAILGUN_TIMEOUT_SECONDS", "15"))
except ValueError:
    MAILGUN_TIMEOUT_SECONDS = 15.0

# SMTP config from environment
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", "0"))
except ValueError:
    SMTP_PORT = 0
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "").strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "").rstrip("/")
try:
    SMTP_TIMEOUT_SECONDS = float(os.getenv("SMTP_TIMEOUT_SECONDS", "15"))
except ValueError:
    SMTP_TIMEOUT_SECONDS = 15.0


def _frontend_link(path: str) -> str:
    if not FRONTEND_URL:
        return "#"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{FRONTEND_URL}{path}"


def _mailgun_messages_url() -> str:
    if MAILGUN_BASE_URL.endswith("/v3"):
        return f"{MAILGUN_BASE_URL}/{MAILGUN_DOMAIN}/messages"
    return f"{MAILGUN_BASE_URL}/v3/{MAILGUN_DOMAIN}/messages"


def _mailgun_configured() -> bool:
    return bool(MAILGUN_API_KEY and MAILGUN_DOMAIN)


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and SMTP_FROM_EMAIL)


def _send_email_via_mailgun(
    to_email: str,
    subject: str,
    html_body: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> bool:
    from_email = MAILGUN_FROM_EMAIL or SMTP_FROM_EMAIL
    from_name = MAILGUN_FROM_NAME or SMTP_FROM_NAME or from_email
    if not from_email:
        raise RuntimeError("MAILGUN_FROM_EMAIL is required when using Mailgun API")

    data = {
        "from": f"{from_name} <{from_email}>",
        "to": to_email,
        "subject": subject,
        "html": html_body,
    }
    files = []
    if attachments:
        for filename, file_bytes in attachments:
            files.append(
                ("attachment", (filename, file_bytes, "application/octet-stream"))
            )

    response = httpx.post(
        _mailgun_messages_url(),
        data=data,
        files=files or None,
        auth=("api", MAILGUN_API_KEY),
        timeout=MAILGUN_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        snippet = response.text.strip().replace("\n", " ")
        raise RuntimeError(
            f"Mailgun API error {response.status_code}: {snippet[:500]}"
        )

    logger.info("✅ Email sent to %s via Mailgun: %s", to_email, subject)
    return True


def _send_email(
    to_email: str,
    subject: str,
    html_body: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> bool:
    """Send an email. Mailgun API is preferred; SMTP is fallback.

    Args:
        attachments: Optional list of (filename, file_bytes) tuples.
    """
    if _mailgun_configured():
        try:
            return _send_email_via_mailgun(to_email, subject, html_body, attachments)
        except Exception as e:
            logger.error("❌ Mailgun send failed to %s: %s", to_email, str(e))
            raise

    if not _smtp_configured():
        logger.warning(
            "Email provider not configured — email to %s skipped (subject: %s)",
            to_email,
            subject,
        )
        logger.info("Email content preview:\n%s", html_body[:500])
        if attachments:
            logger.info("Would attach %d file(s): %s", len(attachments), [a[0] for a in attachments])
        return False

    try:
        msg = MIMEMultipart("mixed")
        from_display_name = SMTP_FROM_NAME or SMTP_FROM_EMAIL
        msg["From"] = f"{from_display_name} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # HTML body
        html_part = MIMEMultipart("alternative")
        html_part.attach(MIMEText(html_body, "html"))
        msg.attach(html_part)

        # Attachments
        if attachments:
            for filename, file_bytes in attachments:
                part = MIMEApplication(file_bytes, Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(part)

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS)
        try:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        finally:
            # Some SMTP providers can return 250 on QUIT; treat that as non-fatal.
            try:
                server.quit()
            except smtplib.SMTPResponseException as close_exc:
                if close_exc.smtp_code not in (221, 250):
                    raise
            except Exception:
                server.close()

        logger.info("✅ Email sent to %s: %s", to_email, subject)
        return True
    except Exception as e:
        logger.error("❌ Email send failed to %s: %s", to_email, str(e))
        raise


# ── Celery Tasks ─────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_order_confirmation",
)
def send_order_confirmation(self, order_data: dict):
    """Send order confirmation email to customer."""
    try:
        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">🧁 Kabul Sweets</h1>
                <p style="color: #666; margin-top: 5px;">Order Confirmation</p>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                <h2 style="color: #1a1a2e; margin-top: 0;">Thank you, {order_data.get('customer_name', 'Valued Customer')}!</h2>
                <p style="color: #444;">Your order <strong>{order_data.get('order_number', '')}</strong> has been received.</p>

                <div style="border-top: 1px solid #eee; margin: 20px 0; padding-top: 15px;">
                    <p style="margin: 5px 0;"><strong>Total:</strong> ${order_data.get('total', '0.00')} AUD</p>
                    <p style="margin: 5px 0;"><strong>Pickup:</strong> {order_data.get('pickup_date', 'TBD')}</p>
                    {f'<p style="margin: 5px 0;"><strong>Cake Message:</strong> "{order_data.get("cake_message")}"</p>' if order_data.get('cake_message') else ''}
                </div>

                <div style="text-align: center; margin-top: 25px;">
                    <a href="{_frontend_link(f"/orders/{order_data.get('order_id', '')}")}"
                       style="background: #7C3AED; color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600;">
                        View Order
                    </a>
                </div>
            </div>
            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 25px;">
                Kabul Sweets — Authentic Afghan Bakery
            </p>
        </div>
        """

        _send_email(
            to_email=order_data.get("customer_email", ""),
            subject=f"Order Confirmed — {order_data.get('order_number', '')} | Kabul Sweets",
            html_body=html,
        )
    except Exception as exc:
        logger.error("Order confirmation email failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_payment_receipt",
)
def send_payment_receipt(self, order_data: dict):
    """Send payment receipt email after successful payment."""
    try:
        items_html = ""
        for item in order_data.get("items", []):
            name = item.get("product_name", "")
            variant = f" ({item.get('variant_name')})" if item.get("variant_name") else ""
            qty = item.get("quantity", 1)
            total = item.get("line_total", "0.00")
            items_html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;">{name}{variant}</td><td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{qty}</td><td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">${total}</td></tr>'

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">🧁 Kabul Sweets</h1>
                <p style="color: #27ae60; font-weight: 600; margin-top: 5px;">✅ Payment Received</p>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                <p style="color: #444;">Order <strong>{order_data.get('order_number', '')}</strong></p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <thead>
                        <tr style="background: #f8f8f8;">
                            <th style="padding: 10px 8px; text-align: left;">Item</th>
                            <th style="padding: 10px 8px; text-align: center;">Qty</th>
                            <th style="padding: 10px 8px; text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>{items_html}</tbody>
                </table>
                <div style="border-top: 2px solid #1a1a2e; padding-top: 12px; margin-top: 10px;">
                    <p style="margin: 4px 0;"><strong>Subtotal:</strong> ${order_data.get('subtotal', '0.00')}</p>
                    <p style="margin: 4px 0;"><strong>GST (10%):</strong> ${order_data.get('tax_amount', '0.00')}</p>
                    <p style="margin: 4px 0; font-size: 18px;"><strong>Total Paid:</strong> ${order_data.get('total', '0.00')} AUD</p>
                </div>
            </div>
            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 25px;">
                This is your official receipt. Keep for your records.
            </p>
        </div>
        """

        # Generate PDF receipt
        pdf_bytes = None
        try:
            from app.services.receipt_service import generate_receipt_pdf
            pdf_bytes = generate_receipt_pdf(order_data)
        except Exception as pdf_err:
            logger.warning("PDF receipt generation failed (sending HTML only): %s", str(pdf_err))

        attachments = []
        if pdf_bytes:
            filename = f"Receipt_{order_data.get('order_number', 'order')}.pdf"
            attachments.append((filename, pdf_bytes))

        _send_email(
            to_email=order_data.get("customer_email", ""),
            subject=f"Receipt — {order_data.get('order_number', '')} | Kabul Sweets",
            html_body=html,
            attachments=attachments if attachments else None,
        )
    except Exception as exc:
        logger.error("Payment receipt email failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_custom_cake_payment_email",
)
def send_custom_cake_payment_email(self, data: dict):
    """Send payment link email to customer after custom cake approval."""
    try:
        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">Kabul Sweets</h1>
                <p style="color: #7C3AED; font-weight: 600; margin-top: 5px;">Custom Cake Approved!</p>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                <h2 style="color: #1a1a2e; margin-top: 0;">Great news, {data.get('customer_name', 'Valued Customer')}!</h2>
                <p style="color: #444;">Your custom cake has been approved and is ready for payment.</p>

                <div style="border-top: 1px solid #eee; margin: 20px 0; padding-top: 15px;">
                    <p style="margin: 5px 0;"><strong>Cake:</strong> {data.get('cake_description', '')}</p>
                    <p style="margin: 5px 0; font-size: 20px;"><strong>Price:</strong> ${data.get('final_price', '0.00')} AUD</p>
                </div>

                <div style="text-align: center; margin-top: 25px;">
                    <a href="{data.get('payment_url', '#')}"
                       style="background: #7C3AED; color: white; padding: 14px 35px; border-radius: 25px; text-decoration: none; font-weight: 600; font-size: 16px;">
                        Pay Now
                    </a>
                </div>

                <p style="color: #999; font-size: 13px; text-align: center; margin-top: 20px;">
                    This link will take you to our secure payment page.
                </p>
            </div>
            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 25px;">
                Kabul Sweets — Authentic Afghan Bakery
            </p>
        </div>
        """

        _send_email(
            to_email=data.get("customer_email", ""),
            subject="Your Custom Cake is Approved — Pay Now | Kabul Sweets",
            html_body=html,
        )
    except Exception as exc:
        logger.error("Custom cake payment email failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_order_rejection_email",
)
def send_order_rejection_email(self, order_data: dict):
    """Send order rejection email with admin-provided reason."""
    try:
        reason = order_data.get("rejection_reason") or "Your order could not be approved at this time."
        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">Kabul Sweets</h1>
                <p style="color: #c0392b; font-weight: 600; margin-top: 5px;">Order Update</p>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                <h2 style="color: #1a1a2e; margin-top: 0;">Hi {order_data.get('customer_name', 'Valued Customer')},</h2>
                <p style="color: #444;">
                    Your order <strong>{order_data.get('order_number', '')}</strong> was not approved by our team.
                </p>
                <div style="border-top: 1px solid #eee; margin: 18px 0; padding-top: 14px;">
                    <p style="margin: 5px 0;"><strong>Reason:</strong> {reason}</p>
                    <p style="margin: 5px 0;"><strong>Total:</strong> ${order_data.get('total', '0.00')} AUD</p>
                    <p style="margin: 5px 0; color: #666;">
                        No charge has been captured. Any authorization hold will be released by your bank.
                    </p>
                </div>
                <div style="text-align: center; margin-top: 24px;">
                    <a href="{_frontend_link('/shop')}"
                       style="background: #7C3AED; color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600;">
                        Place a New Order
                    </a>
                </div>
            </div>
            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 25px;">
                Kabul Sweets — Authentic Afghan Bakery
            </p>
        </div>
        """

        _send_email(
            to_email=order_data.get("customer_email", ""),
            subject=f"Order Update — {order_data.get('order_number', '')} | Kabul Sweets",
            html_body=html,
        )
    except Exception as exc:
        logger.error("Order rejection email failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_abandoned_cart_email",
)
def send_abandoned_cart_email(self, data: dict):
    """Send abandoned cart recovery email."""
    try:
        template = data.get("template", "gentle_reminder")

        if template == "gentle_reminder":
            subject = "You left something behind! | Kabul Sweets"
            heading = "Forgot something?"
            message = "Your cart is waiting for you. Complete your order before your items are gone!"
            button_text = "Return to Cart"
        elif template == "urgency":
            subject = "Your cart is about to expire! | Kabul Sweets"
            heading = "Don't miss out!"
            message = "Items in your cart are selling fast. Complete your order now to secure them!"
            button_text = "Complete Order"
        else:
            subject = "Last chance — your cart expires soon | Kabul Sweets"
            heading = "Last chance!"
            message = "This is your final reminder. Your cart will be cleared soon."
            button_text = "Shop Now"

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">Kabul Sweets</h1>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;">
                <h2 style="color: #1a1a2e; margin-top: 0;">{heading}</h2>
                <p style="color: #444; font-size: 16px;">{message}</p>
                <p style="color: #666;">You have <strong>{data.get('item_count', 0)} item(s)</strong> in your cart.</p>
                <div style="margin-top: 25px;">
                    <a href="{_frontend_link('/cart')}"
                       style="background: #7C3AED; color: white; padding: 14px 35px; border-radius: 25px; text-decoration: none; font-weight: 600;">
                        {button_text}
                    </a>
                </div>
            </div>
            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 25px;">
                Kabul Sweets — Authentic Afghan Bakery
            </p>
        </div>
        """

        _send_email(
            to_email=data.get("customer_email", ""),
            subject=subject,
            html_body=html,
        )
    except Exception as exc:
        logger.error("Abandoned cart email failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_password_reset_email",
)
def send_password_reset_email(self, data: dict):
    """Send password reset email with secure reset link."""
    try:
        reset_token = data.get("reset_token", "")
        encoded_token = quote(reset_token, safe="")
        if not FRONTEND_URL:
            logger.warning("FRONTEND_URL not configured — password reset email skipped")
            return

        reset_link = f"{_frontend_link('/reset-password')}?token={encoded_token}"

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">Kabul Sweets</h1>
                <p style="color: #666; margin-top: 5px;">Password Reset Request</p>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                <h2 style="color: #1a1a2e; margin-top: 0;">Reset your password</h2>
                <p style="color: #444; line-height: 1.6;">
                    We received a request to reset your password. Click the button below to set a new password.
                </p>
                <div style="text-align: center; margin-top: 24px;">
                    <a href="{reset_link}"
                       style="background: #1a1a2e; color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #666; font-size: 13px; margin-top: 20px;">
                    This link expires soon. If you did not request this reset, you can safely ignore this email.
                </p>
            </div>
        </div>
        """

        _send_email(
            to_email=data.get("customer_email", ""),
            subject="Reset your password | Kabul Sweets",
            html_body=html,
        )
    except Exception as exc:
        logger.error("Password reset email failed: %s", str(exc))
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="app.workers.email_tasks.send_order_ready_notification",
)
def send_order_ready_notification(self, order_data: dict):
    """Notify customer their order is ready for pickup."""
    try:
        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #faf7f2; padding: 40px 30px; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1a1a2e; font-size: 28px; margin: 0;">🧁 Kabul Sweets</h1>
            </div>
            <div style="background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;">
                <h2 style="color: #27ae60; margin-top: 0;">🎉 Your Order is Ready!</h2>
                <p style="color: #444; font-size: 16px;">
                    Hi {order_data.get('customer_name', '')}, your order
                    <strong>{order_data.get('order_number', '')}</strong> is ready for pickup!
                </p>
                <p style="color: #666;">Please bring your order number when collecting.</p>
                <div style="margin-top: 25px;">
                    <a href="{_frontend_link(f"/orders/{order_data.get('order_id', '')}")}"
                       style="background: #27ae60; color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600;">
                        View Order Details
                    </a>
                </div>
            </div>
        </div>
        """

        _send_email(
            to_email=order_data.get("customer_email", ""),
            subject=f"Your Order is Ready! — {order_data.get('order_number', '')} | Kabul Sweets",
            html_body=html,
        )
    except Exception as exc:
        logger.error("Order ready notification failed: %s", str(exc))
        self.retry(exc=exc)
