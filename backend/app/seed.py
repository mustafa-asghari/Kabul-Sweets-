"""
Database seed script.
Creates tables, admin user, demo customer, sample products, and test data.
Run with: python -m app.seed
"""

import asyncio
import json
import os
from decimal import Decimal

from sqlalchemy import select

from app.core.database import async_session_factory, engine, Base
from app.core.logging import setup_logging, get_logger
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.product import Product, ProductCategory, ProductVariant, StockAdjustment  # noqa: F401
from app.models.order import Order, OrderItem, Payment  # noqa: F401
from app.models.analytics import AnalyticsEvent, DailyRevenue  # noqa: F401
from app.models.business import ScheduleCapacity, CakeDeposit  # noqa: F401
from app.models.ml import (  # noqa: F401
    CakePricePrediction, ServingEstimate, CustomCake, ProcessedImage, MLModelVersion,
)


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
        "name": "Saffron Milk Cake",
        "slug": "saffron-milk-cake",
        "description": "Luxurious tres leches-style cake infused with saffron and cardamom. Garnished with edible rose petals and gold leaf.",
        "short_description": "Saffron-infused milk cake with rose petals",
        "category": ProductCategory.CAKE,
        "base_price": Decimal("65.00"),
        "is_cake": True,
        "is_featured": True,
        "tags": ["premium", "saffron", "luxury", "wedding"],
        "variants": [
            {"name": "6 inch (serves 6-8)", "price": Decimal("65.00"), "stock_quantity": 6, "serves": 8},
            {"name": "8 inch (serves 10-14)", "price": Decimal("90.00"), "stock_quantity": 4, "serves": 14},
            {"name": "10 inch (serves 16-20)", "price": Decimal("120.00"), "stock_quantity": 3, "serves": 20},
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
        "name": "Baklava Assortment",
        "slug": "baklava-assortment",
        "description": "Hand-layered phyllo pastry filled with walnuts and pistachios, soaked in saffron-infused honey syrup. Afghan-style baklava at its finest.",
        "short_description": "Afghan-style baklava with saffron honey",
        "category": ProductCategory.SWEET,
        "base_price": Decimal("25.00"),
        "is_featured": True,
        "tags": ["premium", "baklava", "pistachio", "gift"],
        "variants": [
            {"name": "Small Box (6 pcs)", "price": Decimal("15.00"), "stock_quantity": 20},
            {"name": "Medium Box (12 pcs)", "price": Decimal("25.00"), "stock_quantity": 15},
            {"name": "Large Box (24 pcs)", "price": Decimal("45.00"), "stock_quantity": 10},
            {"name": "Premium Gift Box (36 pcs)", "price": Decimal("65.00"), "stock_quantity": 5},
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
        "name": "Kulcha-e-Berenji",
        "slug": "kulcha-berenji",
        "description": "Rice flour cookies flavored with cardamom and rosewater. Melt-in-your-mouth Afghan cookies, perfect with chai.",
        "short_description": "Rice flour cookies with cardamom and rosewater",
        "category": ProductCategory.COOKIE,
        "base_price": Decimal("16.00"),
        "tags": ["gluten-free", "traditional", "rosewater"],
        "variants": [
            {"name": "Small Box (12 pcs)", "price": Decimal("16.00"), "stock_quantity": 25},
            {"name": "Large Box (24 pcs)", "price": Decimal("28.00"), "stock_quantity": 15},
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
    {
        "name": "Firni (Milk Pudding)",
        "slug": "firni-milk-pudding",
        "description": "Traditional Afghan milk pudding made with cornstarch, rosewater, and cardamom. Topped with crushed pistachios. Served chilled in beautiful clay bowls.",
        "short_description": "Afghan milk pudding with rosewater",
        "category": ProductCategory.SWEET,
        "base_price": Decimal("10.00"),
        "tags": ["traditional", "dessert", "rosewater"],
        "variants": [
            {"name": "Single Serve", "price": Decimal("10.00"), "stock_quantity": 20},
            {"name": "Family Size (4 serves)", "price": Decimal("35.00"), "stock_quantity": 10},
        ],
    },
]

CATEGORY_IMAGE_SETS = {
    ProductCategory.CAKE: [
        "/products/cake-main.png",
        "/products/cake-alt.png",
    ],
    ProductCategory.PASTRY: [
        "/products/pastry-main.png",
        "/products/pastry-alt.png",
    ],
    ProductCategory.COOKIE: [
        "/products/cookies-main.png",
        "/products/cake-main.png",
    ],
    ProductCategory.SWEET: [
        "/products/sweets-main.png",
        "/products/pastry-main.png",
    ],
    ProductCategory.BREAD: [
        "/products/pastry-alt.png",
        "/products/pastry-main.png",
    ],
    ProductCategory.DRINK: [
        "/products/pastry-alt.png",
        "/products/cookies-main.png",
    ],
    ProductCategory.OTHER: [
        "/products/pastry-main.png",
    ],
}


async def seed_database():
    """Seed the database with initial data."""
    setup_logging()
    logger = get_logger("seed")
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "").strip()
    admin_full_name = os.getenv("SEED_ADMIN_FULL_NAME", "").strip()
    admin_phone = os.getenv("SEED_ADMIN_PHONE", "").strip()
    demo_customers_raw = os.getenv("SEED_DEMO_CUSTOMERS_JSON", "").strip()
    demo_customers: list[dict] = []

    if demo_customers_raw:
        try:
            parsed = json.loads(demo_customers_raw)
            if isinstance(parsed, list):
                demo_customers = [item for item in parsed if isinstance(item, dict)]
            else:
                logger.warning("SEED_DEMO_CUSTOMERS_JSON must be a JSON array. Skipping demo users.")
        except json.JSONDecodeError:
            logger.warning("SEED_DEMO_CUSTOMERS_JSON is invalid JSON. Skipping demo users.")

    logger.info("🌱 Starting database seed...")

    # Create ALL tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")

    async with async_session_factory() as session:
        # ── Admin User ───────────────────────────────────────────────────
        if admin_email and admin_password:
            result = await session.execute(
                select(User).where(User.email == admin_email)
            )
            if not result.scalar_one_or_none():
                resolved_admin_full_name = admin_full_name or admin_email.split("@")[0]
                admin = User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    full_name=resolved_admin_full_name,
                    phone=admin_phone or None,
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_verified=True,
                )
                session.add(admin)
                await session.commit()
                logger.info("✅ Admin user created: %s", admin_email)
            else:
                logger.info("⏭️  Admin user already exists")
        else:
            logger.info("⏭️  SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD not set — skipping admin user seed")

        # ── Demo Customers ───────────────────────────────────────────────
        for cust in demo_customers:
            email = str(cust.get("email", "")).strip().lower()
            password = str(cust.get("password", "")).strip()
            full_name = str(cust.get("full_name", "")).strip() or (email.split("@")[0] if email else "")
            phone = str(cust.get("phone", "")).strip()

            if not email or not password:
                logger.warning("Skipping demo customer without email/password: %s", cust)
                continue

            result = await session.execute(
                select(User).where(User.email == email)
            )
            if not result.scalar_one_or_none():
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    phone=phone or None,
                    role=UserRole.CUSTOMER,
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.commit()
                logger.info("✅ Customer created: %s", email)
            else:
                logger.info("⏭️  Customer %s already exists", email)

        # ── Sample Products ──────────────────────────────────────────────
        result = await session.execute(select(Product).limit(1))
        if result.scalar_one_or_none():
            logger.info("⏭️  Products already exist — backfilling missing image fields")
            products_result = await session.execute(select(Product))
            existing_products = products_result.scalars().all()
            updated_count = 0

            for product in existing_products:
                default_images = CATEGORY_IMAGE_SETS.get(
                    product.category, CATEGORY_IMAGE_SETS[ProductCategory.OTHER]
                )
                changed = False
                if not product.thumbnail:
                    product.thumbnail = default_images[0]
                    changed = True
                if not product.images:
                    product.images = default_images
                    changed = True
                if changed:
                    updated_count += 1

            if updated_count > 0:
                await session.commit()
                logger.info("✅ Backfilled thumbnails/images for %d products", updated_count)
            else:
                logger.info("⏭️  Existing products already have image data")
        else:
            for prod_data in SAMPLE_PRODUCTS:
                variants_data = prod_data.pop("variants", [])
                category = prod_data.get("category", ProductCategory.OTHER)
                default_images = CATEGORY_IMAGE_SETS.get(
                    category, CATEGORY_IMAGE_SETS[ProductCategory.OTHER]
                )
                if not prod_data.get("thumbnail"):
                    prod_data["thumbnail"] = default_images[0]
                if not prod_data.get("images"):
                    prod_data["images"] = default_images
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
            logger.info("✅ %d sample products created with variants", len(SAMPLE_PRODUCTS))

    # ── Summary ──────────────────────────────────────────────────────────
    async with async_session_factory() as session:
        user_count = (await session.execute(select(User))).scalars().all()
        product_count = (await session.execute(select(Product))).scalars().all()
        variant_count = (await session.execute(select(ProductVariant))).scalars().all()

        logger.info("═" * 50)
        logger.info("🌱 Database seed complete!")
        logger.info("  Users:    %d", len(user_count))
        logger.info("  Products: %d", len(product_count))
        logger.info("  Variants: %d", len(variant_count))
        logger.info("═" * 50)
        if admin_email:
            logger.info("  Seed admin email: %s", admin_email)
        if demo_customers:
            logger.info("  Seed demo users: %d", len(demo_customers))
        logger.info("")


if __name__ == "__main__":
    if os.getenv("APP_ENV") == "production":
        print("❌ Seeding is disabled in production. Set APP_ENV to 'development' to seed.")
        raise SystemExit(1)

    asyncio.run(seed_database())
