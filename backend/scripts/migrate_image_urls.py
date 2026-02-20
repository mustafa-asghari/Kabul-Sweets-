#!/usr/bin/env python3
"""
One-time migration: rewrite product image URLs from /original → /serve.

Products created before the public /serve endpoint existed have their
thumbnail and image URLs stored as /api/v1/images/{id}/original.
This script rewrites them to /api/v1/images/{id}/serve in-place so the
frontend can serve them without admin authentication.

Run once directly against the production database:

    cd backend
    python scripts/migrate_image_urls.py

Or via Railway CLI:
    railway run python backend/scripts/migrate_image_urls.py
"""

import asyncio
import re
import sys
from pathlib import Path

# Make sure the backend package is importable.
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

ORIGINAL_PATTERN = re.compile(
    r"(/api/v1/images/[0-9a-f-]+)/original(\b|$)", re.IGNORECASE
)


def rewrite(url: str) -> str:
    """Replace /original with /serve in an image URL."""
    return ORIGINAL_PATTERN.sub(r"\1/serve\2", url)


async def run_migration() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── 1. Fix product thumbnails ────────────────────────────────────────
        result = await session.execute(
            text(
                """
                SELECT id, thumbnail
                FROM products
                WHERE thumbnail LIKE '%/original%'
                """
            )
        )
        rows = result.fetchall()
        thumbnail_updates = 0
        for row in rows:
            new_thumb = rewrite(row.thumbnail)
            if new_thumb != row.thumbnail:
                await session.execute(
                    text("UPDATE products SET thumbnail = :t WHERE id = :id"),
                    {"t": new_thumb, "id": str(row.id)},
                )
                print(f"  thumbnail {row.id}: {row.thumbnail!r}  →  {new_thumb!r}")
                thumbnail_updates += 1

        # ── 2. Fix product images JSON arrays ────────────────────────────────
        result = await session.execute(
            text(
                """
                SELECT id, images
                FROM products
                WHERE images::text LIKE '%/original%'
                """
            )
        )
        rows = result.fetchall()
        images_updates = 0
        for row in rows:
            if not row.images:
                continue
            new_images = [rewrite(url) if isinstance(url, str) else url for url in row.images]
            if new_images != list(row.images):
                import json
                await session.execute(
                    text("UPDATE products SET images = :imgs::jsonb WHERE id = :id"),
                    {"imgs": json.dumps(new_images), "id": str(row.id)},
                )
                print(f"  images   {row.id}: rewrote {len(new_images)} URL(s)")
                images_updates += 1

        await session.commit()

    await engine.dispose()

    print(
        f"\nDone. "
        f"thumbnail column: {thumbnail_updates} row(s) updated. "
        f"images column: {images_updates} row(s) updated."
    )


if __name__ == "__main__":
    asyncio.run(run_migration())
