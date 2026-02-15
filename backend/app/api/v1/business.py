"""
Business endpoints — Phase 13.
Scheduling capacity.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.business_service import SchedulingService

router = APIRouter(tags=["Business"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class SlotAvailabilityResponse(BaseModel):
    time_slot: str
    available: bool
    remaining: int
    cake_remaining: int


# ── Scheduling Endpoints ────────────────────────────────────────────────────
@router.get("/schedule/available", response_model=list[SlotAvailabilityResponse])
async def get_available_slots(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """Get available pickup time slots for a date."""
    try:
        dt = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    service = SchedulingService(db)
    return await service.get_available_slots(dt)
