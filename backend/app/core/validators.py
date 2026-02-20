"""
Business rule validators — enforce every rule the frontend enforces, plus more.

These run server-side on every request regardless of what the client sends.
An attacker with a valid JWT and a crafted payload will still be rejected here.

Rules are grouped by domain:
  • Image uploads  — magic-byte checks, size limits
  • Custom cakes   — allowed diameters, layers, shapes, advance booking window
  • Orders         — quantity caps, stock checks
  • Prices         — sane monetary range
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException

# ── Image upload rules ────────────────────────────────────────────────────────

# Allowed MIME types for any image upload
ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
})

# File-magic signatures → canonical MIME type
# We check the raw bytes, NOT the Content-Type header, to prevent spoofing.
_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),             # JPEG
    (b"\x89PNG\r\n\x1a\n", "image/png"),         # PNG
    (b"RIFF", "image/webp"),                     # WebP (needs secondary check)
    (b"GIF87a", "image/gif"),                    # GIF 87a
    (b"GIF89a", "image/gif"),                    # GIF 89a
]

MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024    # 10 MB hard cap
MAX_BATCH_IMAGES: int = 10                      # max files in one batch upload


def validate_image_magic_bytes(data: bytes) -> str:
    """
    Inspect the raw file header to confirm the bytes match a supported image format.
    Returns the detected MIME type.
    Raises HTTP 415 if the bytes don't match any known image signature.

    This prevents renamed executables, PHP scripts, etc. from slipping through.
    """
    for magic, mime in _MAGIC:
        if data[: len(magic)] == magic:
            # WebP has an extra four-byte 'WEBP' marker at offset 8
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime

    raise HTTPException(
        status_code=415,
        detail=(
            "Unsupported file format. "
            "Only JPEG, PNG, WebP, and GIF images are accepted."
        ),
    )


def validate_image_size(data: bytes) -> None:
    """Reject files that exceed the hard size cap."""
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        mb = MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum allowed size is {mb} MB.",
        )


# ── Custom cake rules ─────────────────────────────────────────────────────────

# Exact diameters the bakery offers — any other value is rejected outright.
ALLOWED_CAKE_DIAMETERS_INCHES: frozenset[float] = frozenset({
    4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 14.0
})

MIN_CAKE_HEIGHT_INCHES: float = 1.0
MAX_CAKE_HEIGHT_INCHES: float = 12.0

MIN_CAKE_LAYERS: int = 1
MAX_CAKE_LAYERS: int = 6

ALLOWED_CAKE_SHAPES: frozenset[str] = frozenset({
    "round", "square", "rectangle", "heart", "hexagon", "number",
})

ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({
    "birthday", "wedding", "anniversary", "graduation", "baby_shower",
    "engagement", "corporate", "eid", "nowruz", "other",
})

# Advance booking window for custom cakes
MIN_ADVANCE_BOOKING_DAYS: int = 3   # must be at least 3 days from now
MAX_ADVANCE_BOOKING_DAYS: int = 90  # cannot book more than 90 days out

# Cake message length cap (prevents oversized text)
MAX_CAKE_MESSAGE_LENGTH: int = 200


def validate_custom_cake(
    diameter_inches: float,
    height_inches: float,
    layers: int,
    shape: str,
    event_type: Optional[str] = None,
    requested_date: Optional[datetime] = None,
    cake_message: Optional[str] = None,
) -> None:
    """
    Enforce all custom cake business rules in one call.
    Raises HTTP 422 for any violated rule.
    """
    # --- Diameter must be one of the bakery's offered sizes ------------------
    # Round to one decimal to tolerate minor float drift (e.g., 8.0 == 8)
    rounded = round(float(diameter_inches), 1)
    if rounded not in ALLOWED_CAKE_DIAMETERS_INCHES:
        allowed = sorted(ALLOWED_CAKE_DIAMETERS_INCHES)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cake diameter must be one of {allowed} inches. "
                f"Received: {diameter_inches}."
            ),
        )

    # --- Height --------------------------------------------------------------
    if not (MIN_CAKE_HEIGHT_INCHES <= height_inches <= MAX_CAKE_HEIGHT_INCHES):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cake height must be between {MIN_CAKE_HEIGHT_INCHES} and "
                f"{MAX_CAKE_HEIGHT_INCHES} inches."
            ),
        )

    # --- Layers --------------------------------------------------------------
    if not (MIN_CAKE_LAYERS <= layers <= MAX_CAKE_LAYERS):
        raise HTTPException(
            status_code=422,
            detail=f"Layers must be between {MIN_CAKE_LAYERS} and {MAX_CAKE_LAYERS}.",
        )

    # --- Shape ---------------------------------------------------------------
    if shape.lower() not in ALLOWED_CAKE_SHAPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Shape must be one of: {sorted(ALLOWED_CAKE_SHAPES)}."
            ),
        )

    # --- Event type (optional field) ----------------------------------------
    if event_type and event_type.lower() not in ALLOWED_EVENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Event type must be one of: {sorted(ALLOWED_EVENT_TYPES)}.",
        )

    # --- Cake message length -------------------------------------------------
    if cake_message and len(cake_message) > MAX_CAKE_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Cake message cannot exceed {MAX_CAKE_MESSAGE_LENGTH} characters.",
        )

    # --- Requested date (advance booking window) ----------------------------
    if requested_date:
        now = datetime.now(timezone.utc)
        # Normalise tz-naive datetimes to UTC
        if requested_date.tzinfo is None:
            requested_date = requested_date.replace(tzinfo=timezone.utc)

        earliest = now + timedelta(days=MIN_ADVANCE_BOOKING_DAYS)
        latest = now + timedelta(days=MAX_ADVANCE_BOOKING_DAYS)

        if requested_date < earliest:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Custom cakes require at least {MIN_ADVANCE_BOOKING_DAYS} days "
                    "advance notice. Please choose a later date."
                ),
            )
        if requested_date > latest:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Orders cannot be placed more than {MAX_ADVANCE_BOOKING_DAYS} "
                    "days in advance."
                ),
            )


# ── Order / quantity rules ────────────────────────────────────────────────────

MAX_QUANTITY_PER_LINE: int = 50   # single line item cap
MAX_LINES_PER_ORDER: int = 20     # total distinct items in one order


def validate_order_quantity(
    quantity: int,
    product_max_per_order: Optional[int] = None,
    stock_quantity: Optional[int] = None,
) -> None:
    """
    Reject order quantities that are impossible or exceed product/stock limits.
    Raises HTTP 422 on any violation.
    """
    if quantity < 1:
        raise HTTPException(status_code=422, detail="Quantity must be at least 1.")

    if quantity > MAX_QUANTITY_PER_LINE:
        raise HTTPException(
            status_code=422,
            detail=f"Maximum quantity per item is {MAX_QUANTITY_PER_LINE}.",
        )

    if product_max_per_order is not None and quantity > product_max_per_order:
        raise HTTPException(
            status_code=422,
            detail=f"This product is limited to {product_max_per_order} per order.",
        )

    if stock_quantity is not None and quantity > stock_quantity:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Requested quantity ({quantity}) exceeds available stock "
                f"({stock_quantity})."
            ),
        )


def validate_order_line_count(line_count: int) -> None:
    """Reject orders with too many distinct items."""
    if line_count > MAX_LINES_PER_ORDER:
        raise HTTPException(
            status_code=422,
            detail=f"An order cannot contain more than {MAX_LINES_PER_ORDER} different items.",
        )


# ── Price rules ───────────────────────────────────────────────────────────────

MIN_PRICE: float = 0.01
MAX_PRICE: float = 9_999.99


def validate_price(price: float, field: str = "Price") -> None:
    """Ensure a monetary value is in a realistic range."""
    if price < MIN_PRICE:
        raise HTTPException(
            status_code=422,
            detail=f"{field} must be at least ${MIN_PRICE:.2f}.",
        )
    if price > MAX_PRICE:
        raise HTTPException(
            status_code=422,
            detail=f"{field} cannot exceed ${MAX_PRICE:,.2f}.",
        )


# ── String / text rules ───────────────────────────────────────────────────────

def validate_non_empty_string(value: str, field: str, max_len: int = 1000) -> str:
    """Strip, non-empty, and length-cap a free-text field."""
    stripped = (value or "").strip()
    if not stripped:
        raise HTTPException(status_code=422, detail=f"{field} cannot be empty.")
    if len(stripped) > max_len:
        raise HTTPException(
            status_code=422,
            detail=f"{field} cannot exceed {max_len} characters.",
        )
    return stripped
