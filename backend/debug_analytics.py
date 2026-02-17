import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Assuming we are in /app directory if container, or /Users/mustafaasghari/code/Kabul_Sweets/code/backend
# Setup correct path for importing
sys.path.append(os.path.abspath("/Users/mustafaasghari/code/Kabul_Sweets/code/backend"))

from app.core.database import async_session_factory as async_session_maker
from app.services.analytics_service import AnalyticsService

async def debug_worst_sellers():
    async with async_session_maker() as db:
        service = AnalyticsService(db)
        print("Running get_worst_sellers...")
        try:
            items = await service.get_worst_sellers(days=30, limit=10)
            print("Received items:", len(items))
            for item in items:
                print(item)
                if item.get("product_id") is None:
                    print("ERROR: FOUND ITEM WITH None PRODUCT_ID!")
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_worst_sellers())
