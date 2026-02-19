import asyncio
import uuid
import os
import sys

# Add the project root to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.config import get_settings
from app.core.database import Base
from app.models.user import User
from app.models.ml import CustomCake, CustomCakeStatus
from app.services.custom_cake_service import CustomCakeService

settings = get_settings()

async def reproduction_script():
    # Setup database connection
    engine = create_async_engine(str(settings.DATABASE_URL))
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as db:
        # 1. Create a dummy test user
        test_email = f"test_user_{uuid.uuid4()}@example.com"
        user = User(
            email=test_email,
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"Created test user: {user.id} ({user.email})")

        # 2. Submit a custom cake for this user
        service = CustomCakeService(db)
        
        print("Submitting custom cake...")
        cake_data = await service.submit_custom_cake(
            customer_id=user.id,
            flavor="Spong + Vanila",
            diameter_inches=10.0,
            height_inches=4.0,
            layers=1,
            shape="round",
            decoration_complexity="moderate",
            cake_message="Happy Testing",
            is_rush_order=False
        )
        cake_id = uuid.UUID(cake_data["custom_cake_id"])
        print(f"Custom cake submitted: {cake_id}")
        
        # 3. List custom cakes for this user (simulating get_my_custom_cakes)
        # Verify the service method being used by the API endpoint
        print("Fetching customer's cakes...")
        
        # The API endpoint does this:
        # await service.purge_cancelled_cakes_for_customer(current_user.id)
        # cakes = await service.list_custom_cakes(customer_id=current_user.id)
        
        purged_count = await service.purge_cancelled_cakes_for_customer(user.id)
        print(f"Purged {purged_count} cancelled cakes.")
        
        cakes = await service.list_custom_cakes(customer_id=user.id)
        
        # Filter as the API does
        visible_cakes = [
            c for c in cakes
            if c.status != CustomCakeStatus.CANCELLED
        ]
        
        print(f"Found {len(visible_cakes)} visible cakes.")
        for c in visible_cakes:
            print(f" - Cake {c.id}: Status={c.status.value}, Flavor={c.flavor}")
            
        success = False
        for c in visible_cakes:
            if c.id == cake_id:
                success = True
                break
        
        if success:
            print("SUCCESS: The submitted custom cake was found in the list.")
        else:
            print("FAILURE: The submitted custom cake was NOT found.")

        # Cleanup
        print("Cleaning up...")
        await db.delete(user) # Cascade should delete the cake too
        await db.commit()

if __name__ == "__main__":
    asyncio.run(reproduction_script())
