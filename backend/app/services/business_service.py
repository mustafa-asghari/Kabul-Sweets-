"""
Business service — Phase 13.
Scheduling capacity management.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.business import ScheduleCapacity

logger = get_logger("business_service")


class SchedulingService:
    """Manages order scheduling capacity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_availability(
        self,
        date: datetime,
        time_slot: str,
        is_cake: bool = False,
    ) -> tuple[bool, str]:
        """Check if a time slot has capacity."""
        result = await self.db.execute(
            select(ScheduleCapacity).where(
                ScheduleCapacity.date == date,
                ScheduleCapacity.time_slot == time_slot,
            )
        )
        capacity = result.scalar_one_or_none()

        if not capacity:
            return True, "Available"

        if not capacity.has_capacity(is_cake):
            if capacity.is_blocked:
                return False, "This time slot is not available"
            return False, "This time slot is fully booked"

        return True, f"{capacity.max_orders - capacity.current_orders} slots remaining"

    async def reserve_slot(
        self,
        date: datetime,
        time_slot: str,
        is_cake: bool = False,
    ) -> bool:
        """Reserve a slot for an order."""
        result = await self.db.execute(
            select(ScheduleCapacity).where(
                ScheduleCapacity.date == date,
                ScheduleCapacity.time_slot == time_slot,
            )
        )
        capacity = result.scalar_one_or_none()

        if not capacity:
            capacity = ScheduleCapacity(date=date, time_slot=time_slot)
            self.db.add(capacity)

        if not capacity.has_capacity(is_cake):
            return False

        capacity.current_orders += 1
        if is_cake:
            capacity.current_cake_orders += 1

        await self.db.flush()
        return True

    async def get_available_slots(self, date: datetime) -> list[dict]:
        """Get all available time slots for a date."""
        DEFAULT_SLOTS = [
            "09:00-10:00", "10:00-11:00", "11:00-12:00",
            "12:00-13:00", "13:00-14:00", "14:00-15:00",
            "15:00-16:00", "16:00-17:00",
        ]

        result = await self.db.execute(
            select(ScheduleCapacity).where(ScheduleCapacity.date == date)
        )
        existing = {cap.time_slot: cap for cap in result.scalars().all()}

        slots = []
        for slot in DEFAULT_SLOTS:
            if slot in existing:
                cap = existing[slot]
                slots.append({
                    "time_slot": slot,
                    "available": cap.has_capacity(),
                    "remaining": max(0, cap.max_orders - cap.current_orders),
                    "cake_remaining": max(0, cap.max_cake_orders - cap.current_cake_orders),
                })
            else:
                slots.append({
                    "time_slot": slot,
                    "available": True,
                    "remaining": 10,
                    "cake_remaining": 5,
                })

        return slots
