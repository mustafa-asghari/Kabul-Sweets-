import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def run():
    async with async_session() as ds:
        res = await ds.execute(text("SELECT id, name, slug, is_active FROM products WHERE id = 'a99f1046-fdd6-4fa7-bea5-79e449ac4c9d'"))
        row = res.fetchone()
        if row:
            print("Product:", dict(row._mapping))
        else:
            print("Product not found")
        
        # also print the cart item directly
        res2 = await ds.execute(text("SELECT * FROM cart_items WHERE product_id = 'a99f1046-fdd6-4fa7-bea5-79e449ac4c9d'"))
        rows2 = res2.fetchall()
        print("Cart Items:")
        for r in rows2:
            print(dict(r._mapping))

asyncio.run(run())
