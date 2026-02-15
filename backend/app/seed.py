"""
Database seed script.
Creates tables, admin user, and sample products.
Run with: python -m app.seed
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.database import async_session_factory, engine, Base
from app.core.logging import setup_logging, get_logger
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.product import Product, ProductCategory, ProductVariant, StockAdjustment  # noqa: F401
from app.models.order import Order, OrderItem, Payment  # noqa: F401


SAMPLE_PRODUCTS = [
    {
        "name": "Afghan Walnut Cake",
        "slug": "afghan-walnut-cake",
        "description": "Traditional Afghan walnut cake made with love. Rich, moist, and topped with caramelized walnuts. A Kabul Sweets signature.",
        "short_description": "Traditional Afghan walnut cake with caramelized walnuts",
        "category": ProductCategory.CAKE,
        "base_price": Decimal("45.00"),
        "is_cake": True,
        "is_featured": True,
        "tags": ["signature", "traditional", "nut-free-option-unavailable"],
        "variants": [
            {"name": "6 inch (serves 6-8)", "price": Decimal("45.00"), "stock_quantity": 10, "serves": 8},
            {"name": "8 inch (serves 10-14)", "price": Decimal("65.00"), "stock_quantity": 8, "serves": 14},
            {"name": "10 inch (serves 16-20)", "price": Decimal("85.00"), "stock_quantity": 5, "serves": 20},
        ],
    },
    {
        "name": "Rose & Pistachio Cake",
        "slug": "rose-pistachio-cake",
        "description": "Delicate sponge cake infused with rosewater and decorated with crushed pistachios. A fusion of Afghan and Persian flavors.",
        "short_description": "Rosewater sponge with crushed pistachio topping",
        "category": ProductCategory.CAKE,
        "base_price": Decimal("55.00"),
        "is_cake": True,
        "is_featured": True,
        "tags": ["premium", "persian", "rosewater"],
        "variants": [
            {"name": "6 inch (serves 6-8)", "price": Decimal("55.00"), "stock_quantity": 8, "serves": 8},
            {"name": "8 inch (serves 10-14)", "price": Decimal("75.00"), "stock_quantity": 6, "serves": 14},
            {"name": "10 inch (serves 16-20)", "price": Decimal("95.00"), "stock_quantity": 4, "serves": 20},
        ],
    },
    {
        "name": "Cardamom Honey Cake",
        "slug": "cardamom-honey-cake",
        "description": "Warm, aromatic cardamom cake drizzled with Afghan mountain honey. Perfect for afternoon chai.",
        "short_description": "Cardamom cake with Afghan mountain honey",
        "category": ProductCategory.CAKE,
        "base_price": Decimal("40.00"),
        "is_cake": True,
        "tags": ["traditional", "honey", "cardamom"],
        "variants": [
            {"name": "6 inch (serves 6-8)", "price": Decimal("40.00"), "stock_quantity": 12, "serves": 8},
            {"name": "8 inch (serves 10-14)", "price": Decimal("60.00"), "stock_quantity": 8, "serves": 14},
        ],
    },
    {
        "name": "Gosh-e-Fil (Elephant Ears)",
        "slug": "gosh-e-fil",
        "description": "Crispy fried pastry dusted with powdered sugar and ground cardamom. A beloved Afghan treat for celebrations.",
        "short_description": "Crispy Afghan pastry with cardamom sugar",
        "category": ProductCategory.PASTRY,
        "base_price": Decimal("12.00"),
        "is_featured": True,
        "tags": ["traditional", "fried", "celebration"],
        "variants": [
            {"name": "Box of 6", "price": Decimal("12.00"), "stock_quantity": 25},
            {"name": "Box of 12", "price": Decimal("22.00"), "stock_quantity": 15},
            {"name": "Party Box (24)", "price": Decimal("40.00"), "stock_quantity": 8},
        ],
    },
    {
        "name": "Sheer Pira (Milk Fudge)",
        "slug": "sheer-pira",
        "description": "Traditional Afghan milk fudge made with condensed milk, sugar, and cardamom. Soft, creamy, and irresistible.",
        "short_description": "Afghan milk fudge with cardamom",
        "category": ProductCategory.SWEET,
        "base_price": Decimal("15.00"),
        "tags": ["traditional", "fudge", "gift"],
        "variants": [
            {"name": "250g Box", "price": Decimal("15.00"), "stock_quantity": 30},
            {"name": "500g Box", "price": Decimal("28.00"), "stock_quantity": 20},
            {"name": "1kg Gift Box", "price": Decimal("50.00"), "stock_quantity": 10},
        ],
    },
    {
        "name": "Afghan Bolani",
        "slug": "afghan-bolani",
        "description": "Stuffed flatbread with potato, leek, or pumpkin filling. Crispy on the outside, savory on the inside.",
        "short_description": "Crispy stuffed Afghan flatbread",
        "category": ProductCategory.BREAD,
        "base_price": Decimal("8.00"),
        "tags": ["savory", "traditional", "vegetarian"],
        "variants": [
            {"name": "Potato (2 pcs)", "price": Decimal("8.00"), "stock_quantity": 40},
            {"name": "Leek (2 pcs)", "price": Decimal("8.00"), "stock_quantity": 30},
            {"name": "Pumpkin (2 pcs)", "price": Decimal("9.00"), "stock_quantity": 25},
            {"name": "Mixed Pack (6 pcs)", "price": Decimal("22.00"), "stock_quantity": 15},
        ],
    },
    {
        "name": "Kulcha-e-Nowrozee",
        "slug": "kulcha-nowrozee",
        "description": "Special Nowroz cookies made only during the Afghan New Year celebration. Delicate shortbread with intricate patterns.",
        "short_description": "Traditional Nowroz celebration cookies",
        "category": ProductCategory.COOKIE,
        "base_price": Decimal("18.00"),
        "tags": ["seasonal", "nowroz", "traditional", "gift"],
        "variants": [
            {"name": "Small Box (12 pcs)", "price": Decimal("18.00"), "stock_quantity": 20},
            {"name": "Large Box (24 pcs)", "price": Decimal("32.00"), "stock_quantity": 12},
        ],
    },
    {
        "name": "Chai Masala Tea",
        "slug": "chai-masala",
        "description": "Authentic Afghan chai spice blend — cardamom, cinnamon, cloves, and black tea. Just add milk and sugar.",
        "short_description": "Afghan spiced tea blend",
        "category": ProductCategory.DRINK,
        "base_price": Decimal("12.00"),
        "tags": ["chai", "spice", "gift"],
        "variants": [
            {"name": "100g Tin", "price": Decimal("12.00"), "stock_quantity": 50},
            {"name": "250g Tin", "price": Decimal("25.00"), "stock_quantity": 30},
        ],
    },
]


async def seed_database():
    """Seed the database with initial data."""
    setup_logging()
    logger = get_logger("seed")

    logger.info("🌱 Starting database seed...")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")

    async with async_session_factory() as session:
        # ── Admin User ───────────────────────────────────────────────────
        result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@kabulsweets.com.au",
                hashed_password=hash_password("Admin@2024!"),
                full_name="Kabul Sweets Admin",
                phone="+61400000000",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("✅ Admin user created: admin@kabulsweets.com.au")
        else:
            logger.info("Admin user already exists")

        # ── Demo Customer ────────────────────────────────────────────────
        result = await session.execute(
            select(User).where(User.role == UserRole.CUSTOMER)
        )
        if not result.scalar_one_or_none():
            customer = User(
                email="customer@example.com",
                hashed_password=hash_password("Customer@2024!"),
                full_name="Demo Customer",
                phone="+61411111111",
                role=UserRole.CUSTOMER,
                is_active=True,
                is_verified=True,
            )
            session.add(customer)
            await session.commit()
            logger.info("✅ Demo customer created: customer@example.com")
        else:
            logger.info("Demo customer already exists")

        # ── Sample Products ──────────────────────────────────────────────
        result = await session.execute(select(Product).limit(1))
        if result.scalar_one_or_none():
            logger.info("Products already exist — skipping product seed")
        else:
            for prod_data in SAMPLE_PRODUCTS:
                variants_data = prod_data.pop("variants", [])
                product = Product(**prod_data)
                session.add(product)
                await session.flush()

                for v in variants_data:
                    variant = ProductVariant(
                        product_id=product.id,
                        name=v["name"],
                        price=v["price"],
                        stock_quantity=v.get("stock_quantity", 10),
                        serves=v.get("serves"),
                        is_in_stock=True,
                    )
                    session.add(variant)

            await session.commit()
            logger.info("✅ %d sample products created", len(SAMPLE_PRODUCTS))

    logger.info("🌱 Database seed complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
