"""
Cart background tasks — abandoned cart detection and recovery emails.
"""

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.celery_app import celery_app
from app.models.cart import Cart, CartItem, CartRecoveryAttempt, CartStatus
from app.models.user import User

logger = logging.getLogger("app.workers.cart")

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg2")
_engine = None


def _get_sync_engine():
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=3)
    return _engine


# Recovery timing: hours since last activity -> template to send
RECOVERY_STEPS = [
    {"min_hours": 1, "max_hours": 24, "template": "gentle_reminder"},
    {"min_hours": 24, "max_hours": 72, "template": "urgency"},
    {"min_hours": 72, "max_hours": 168, "template": "last_chance"},
]


@celery_app.task(
    name="app.workers.cart_tasks.process_abandoned_carts",
    max_retries=2,
)
def process_abandoned_carts():
    """
    Find abandoned carts and send recovery emails.
    Runs every hour via Celery Beat.
    """
    engine = _get_sync_engine()
    if not engine:
        logger.warning("Database not configured — skipping abandoned cart check")
        return

    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        # Find active carts that haven't had the first recovery email sent
        abandoned = session.execute(
            select(Cart).where(
                Cart.status == CartStatus.ACTIVE,
                Cart.recovery_email_sent == False,  # noqa: E712
            )
        ).scalars().all()

        sent_count = 0
        for cart in abandoned:
            # Check if cart has items
            items = session.execute(
                select(CartItem).where(CartItem.cart_id == cart.id)
            ).scalars().all()

            if not items:
                continue

            hours_inactive = (now - cart.last_activity).total_seconds() / 3600

            # Find the right recovery step
            for step in RECOVERY_STEPS:
                if step["min_hours"] <= hours_inactive < step["max_hours"]:
                    # Check if this template was already sent
                    existing = session.execute(
                        select(CartRecoveryAttempt).where(
                            CartRecoveryAttempt.cart_id == cart.id,
                            CartRecoveryAttempt.template == step["template"],
                        )
                    ).scalar_one_or_none()

                    if existing:
                        continue

                    # Get customer email
                    customer = session.execute(
                        select(User).where(User.id == cart.customer_id)
                    ).scalar_one_or_none()

                    if not customer or not customer.email:
                        continue

                    # Record recovery attempt
                    attempt = CartRecoveryAttempt(
                        cart_id=cart.id,
                        channel="email",
                        template=step["template"],
                    )
                    session.add(attempt)

                    if step["template"] == "gentle_reminder":
                        cart.recovery_email_sent = True

                    # Queue the email
                    from app.workers.email_tasks import send_abandoned_cart_email
                    send_abandoned_cart_email.delay({
                        "customer_email": customer.email,
                        "customer_name": customer.full_name,
                        "item_count": len(items),
                        "template": step["template"],
                        "cart_id": str(cart.id),
                    })

                    sent_count += 1
                    logger.info(
                        "Recovery email (%s) queued for cart %s (customer: %s, %d items, %.1f hrs inactive)",
                        step["template"], cart.id, customer.email, len(items), hours_inactive,
                    )
                    break  # Only send one email per cart per run

        session.commit()
        logger.info("Abandoned cart check complete: %d recovery emails queued", sent_count)
