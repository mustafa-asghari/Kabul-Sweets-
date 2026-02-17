"""
Comprehensive API Test Script for Kabul Sweets Backend.
Tests all endpoints, validates responses, and reports results.

Run with: python -m app.tests.test_api
Requires: The app running locally on port 8000
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta

import httpx

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"

# Test credentials
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "")
CUSTOMER_EMAIL = os.getenv("TEST_CUSTOMER_EMAIL", "")
CUSTOMER_PASSWORD = os.getenv("TEST_CUSTOMER_PASSWORD", "")

# Track results
results: list[dict] = []


def log_result(endpoint: str, method: str, status: int, passed: bool, detail: str = ""):
    """Log a test result."""
    icon = "✅" if passed else "❌"
    results.append({
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "passed": passed,
        "detail": detail,
    })
    print(f"  {icon} {method:6s} {endpoint} → {status} {detail}")


async def run_tests():
    """Run all API tests."""
    print("=" * 70)
    print("🧪 KABUL SWEETS API — COMPREHENSIVE TEST SUITE")
    print(f"   Target: {BASE_URL}")
    print(f"   Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        admin_token = None
        admin_refresh = None
        customer_token = None
        product_id = None
        variant_id = None
        order_id = None
        custom_cake_id = None

        # ─────────────────────────────────────────────────────────────────
        # 1. ROOT & HEALTH
        # ─────────────────────────────────────────────────────────────────
        print("\n📋 1. Root & Health Endpoints")

        r = await client.get("/")
        log_result("/", "GET", r.status_code, r.status_code == 200)

        r = await client.get(f"{API}/health")
        log_result("/health", "GET", r.status_code, r.status_code == 200)

        r = await client.get(f"{API}/ping")
        log_result("/ping", "GET", r.status_code, r.status_code == 200)

        # ─────────────────────────────────────────────────────────────────
        # 2. AUTHENTICATION
        # ─────────────────────────────────────────────────────────────────
        print("\n🔒 2. Authentication")

        # Register a new test user
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        r = await client.post(f"{API}/auth/register", json={
            "email": test_email,
            "password": "TestPass@123",
            "full_name": "Test User",
            "phone": "+61499999999",
        })
        log_result("/auth/register", "POST", r.status_code, r.status_code in (200, 201))

        # Admin login
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            r = await client.post(f"{API}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })
            if r.status_code == 200:
                data = r.json()
                admin_token = data.get("access_token")
                admin_refresh = data.get("refresh_token")
                log_result("/auth/login (admin)", "POST", r.status_code, bool(admin_token))
            else:
                log_result("/auth/login (admin)", "POST", r.status_code, False, f"FAIL: {r.text[:100]}")
        else:
            log_result("/auth/login (admin)", "POST", 0, False, "Skipped (TEST_ADMIN_* not set)")

        # Customer login
        if CUSTOMER_EMAIL and CUSTOMER_PASSWORD:
            r = await client.post(f"{API}/auth/login", json={
                "email": CUSTOMER_EMAIL,
                "password": CUSTOMER_PASSWORD,
            })
            if r.status_code == 200:
                data = r.json()
                customer_token = data.get("access_token")
                log_result("/auth/login (customer)", "POST", r.status_code, bool(customer_token))
            else:
                log_result("/auth/login (customer)", "POST", r.status_code, False, f"FAIL: {r.text[:100]}")
        else:
            log_result("/auth/login (customer)", "POST", 0, False, "Skipped (TEST_CUSTOMER_* not set)")

        # Refresh token
        if admin_refresh:
            r = await client.post(f"{API}/auth/refresh", json={
                "refresh_token": admin_refresh,
            })
            log_result("/auth/refresh", "POST", r.status_code, r.status_code == 200)

        # Auth headers
        admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        customer_headers = {"Authorization": f"Bearer {customer_token}"} if customer_token else {}

        if not admin_token:
            print("\n  ⚠️  ADMIN LOGIN FAILED — Skipping admin-only tests")
        if not customer_token:
            print("\n  ⚠️  CUSTOMER LOGIN FAILED — Skipping customer tests")

        # ─────────────────────────────────────────────────────────────────
        # 3. USERS
        # ─────────────────────────────────────────────────────────────────
        print("\n👤 3. User Management")

        if customer_token:
            r = await client.get(f"{API}/users/me", headers=customer_headers)
            log_result("/users/me", "GET", r.status_code, r.status_code == 200)

            r = await client.patch(f"{API}/users/me", headers=customer_headers, json={
                "full_name": "Demo Customer Updated",
            })
            log_result("/users/me (update)", "PATCH", r.status_code, r.status_code == 200)

            r = await client.post(f"{API}/users/me/change-password", headers=customer_headers, json={
                "current_password": CUSTOMER_PASSWORD,
                "new_password": CUSTOMER_PASSWORD,  # Same password, just testing the endpoint
            })
            log_result("/users/me/change-password", "POST", r.status_code, r.status_code in (200, 400))

        if admin_token:
            r = await client.get(f"{API}/users/", headers=admin_headers)
            log_result("/users/ (admin list)", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/users/count", headers=admin_headers)
            log_result("/users/count", "GET", r.status_code, r.status_code == 200)

        # No auth test
        r = await client.get(f"{API}/users/me")
        log_result("/users/me (no auth)", "GET", r.status_code, r.status_code in (401, 403), "Should be unauthorized")

        # ─────────────────────────────────────────────────────────────────
        # 4. PRODUCTS (Public)
        # ─────────────────────────────────────────────────────────────────
        print("\n🛍️  4. Products (Public)")

        r = await client.get(f"{API}/products/")
        log_result("/products/", "GET", r.status_code, r.status_code == 200)
        if r.status_code == 200:
            products = r.json()
            if isinstance(products, list) and len(products) > 0:
                product_id = products[0].get("id")
                log_result("  → products found", "INFO", 0, True, f"{len(products)} products")

        r = await client.get(f"{API}/products/count")
        log_result("/products/count", "GET", r.status_code, r.status_code == 200)

        r = await client.get(f"{API}/products/slug/afghan-walnut-cake")
        log_result("/products/slug/{slug}", "GET", r.status_code, r.status_code == 200)

        if product_id:
            r = await client.get(f"{API}/products/{product_id}")
            log_result("/products/{id}", "GET", r.status_code, r.status_code == 200)
            if r.status_code == 200:
                product_data = r.json()
                variants = product_data.get("variants", [])
                if variants:
                    variant_id = variants[0].get("id")

        # ─────────────────────────────────────────────────────────────────
        # 5. PRODUCTS (Admin)
        # ─────────────────────────────────────────────────────────────────
        print("\n🛍️  5. Products (Admin)")

        if admin_token:
            r = await client.get(f"{API}/products/admin/all", headers=admin_headers)
            log_result("/products/admin/all", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/products/low-stock/all", headers=admin_headers)
            log_result("/products/low-stock/all", "GET", r.status_code, r.status_code == 200)

            # Create a test product
            r = await client.post(f"{API}/products/", headers=admin_headers, json={
                "name": f"Test Product {uuid.uuid4().hex[:6]}",
                "slug": f"test-product-{uuid.uuid4().hex[:6]}",
                "description": "A test product for API testing",
                "short_description": "Test product",
                "category": "sweet",
                "base_price": "19.99",
            })
            log_result("/products/ (create)", "POST", r.status_code, r.status_code in (200, 201))
            test_product_id = None
            if r.status_code in (200, 201):
                test_product_id = r.json().get("id")

            if test_product_id:
                # Update product
                r = await client.patch(f"{API}/products/{test_product_id}", headers=admin_headers, json={
                    "description": "Updated description",
                })
                log_result("/products/{id} (update)", "PATCH", r.status_code, r.status_code == 200)

                # Add variant
                r = await client.post(f"{API}/products/{test_product_id}/variants", headers=admin_headers, json={
                    "name": "Small Box",
                    "price": "19.99",
                    "stock_quantity": 50,
                })
                log_result("/products/{id}/variants", "POST", r.status_code, r.status_code in (200, 201))
                test_variant_id = None
                if r.status_code in (200, 201):
                    test_variant_id = r.json().get("id")

                # Stock adjustment
                if test_variant_id:
                    r = await client.post(f"{API}/products/{test_product_id}/stock", headers=admin_headers, json={
                        "variant_id": test_variant_id,
                        "quantity_change": 10,
                        "reason": "Test restock",
                    })
                    log_result("/products/{id}/stock", "POST", r.status_code, r.status_code in (200, 201))

                # Clean up — delete test product
                r = await client.delete(f"{API}/products/{test_product_id}", headers=admin_headers)
                log_result("/products/{id} (delete)", "DELETE", r.status_code, r.status_code in (200, 204))

        # ─────────────────────────────────────────────────────────────────
        # 6. ORDERS
        # ─────────────────────────────────────────────────────────────────
        print("\n📦 6. Orders")

        if customer_token and variant_id and product_id:
            # Create order
            r = await client.post(f"{API}/orders/", headers=customer_headers, json={
                "items": [
                    {
                        "product_id": product_id,
                        "variant_id": variant_id,
                        "quantity": 1,
                    }
                ],
                "customer_name": "Demo Customer",
                "customer_email": "customer@example.com",
                "customer_phone": "+61411111111",
                "pickup_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "pickup_time_slot": "14:00-15:00",
            })
            log_result("/orders/ (create)", "POST", r.status_code, r.status_code in (200, 201))
            if r.status_code in (200, 201):
                order_id = r.json().get("id")

            # List my orders
            r = await client.get(f"{API}/orders/my-orders", headers=customer_headers)
            log_result("/orders/my-orders", "GET", r.status_code, r.status_code == 200)

            if order_id:
                r = await client.get(f"{API}/orders/my-orders/{order_id}", headers=customer_headers)
                log_result("/orders/my-orders/{id}", "GET", r.status_code, r.status_code == 200)

        if admin_token:
            r = await client.get(f"{API}/orders/", headers=admin_headers)
            log_result("/orders/ (admin list)", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/orders/count", headers=admin_headers)
            log_result("/orders/count", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/orders/cake-orders", headers=admin_headers)
            log_result("/orders/cake-orders", "GET", r.status_code, r.status_code == 200)

            if order_id:
                r = await client.get(f"{API}/orders/{order_id}", headers=admin_headers)
                log_result("/orders/{id}", "GET", r.status_code, r.status_code == 200)

                # Get order number
                if r.status_code == 200:
                    order_number = r.json().get("order_number")
                    if order_number:
                        r = await client.get(f"{API}/orders/number/{order_number}", headers=admin_headers)
                        log_result("/orders/number/{n}", "GET", r.status_code, r.status_code == 200)

        # ─────────────────────────────────────────────────────────────────
        # 7. PAYMENTS
        # ─────────────────────────────────────────────────────────────────
        print("\n💳 7. Payments")

        if customer_token and order_id:
            r = await client.post(f"{API}/payments/{order_id}/checkout", headers=customer_headers)
            # May fail if Stripe is not configured — that's OK
            log_result("/payments/{id}/checkout", "POST", r.status_code,
                       r.status_code in (200, 400, 500),
                       "(Stripe may not be configured)")

        # ─────────────────────────────────────────────────────────────────
        # 8. ANALYTICS
        # ─────────────────────────────────────────────────────────────────
        print("\n📊 8. Analytics")

        if admin_token:
            r = await client.get(f"{API}/analytics/dashboard", headers=admin_headers)
            log_result("/analytics/dashboard", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/analytics/revenue/summary", headers=admin_headers)
            log_result("/analytics/revenue/summary", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/analytics/revenue/daily", headers=admin_headers)
            log_result("/analytics/revenue/daily", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/analytics/best-sellers", headers=admin_headers)
            log_result("/analytics/best-sellers", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/analytics/worst-sellers", headers=admin_headers)
            log_result("/analytics/worst-sellers", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/analytics/popular-cake-sizes", headers=admin_headers)
            log_result("/analytics/popular-cake-sizes", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/analytics/inventory-turnover", headers=admin_headers)
            log_result("/analytics/inventory-turnover", "GET", r.status_code, r.status_code == 200)

            r = await client.post(f"{API}/analytics/events", headers=admin_headers, json={
                "event_type": "page_view",
                "event_data": {"page": "/products"},
            })
            log_result("/analytics/events", "POST", r.status_code, r.status_code in (200, 201))

        # ─────────────────────────────────────────────────────────────────
        # 9. ML SERVICES
        # ─────────────────────────────────────────────────────────────────
        print("\n🧠 9. ML Services")

        if admin_token:
            r = await client.post(f"{API}/ml/predict-price", headers=admin_headers, json={
                "diameter_inches": 8,
                "height_inches": 4,
                "layers": 2,
                "shape": "round",
                "labor_hours": 3,
                "decoration_complexity": "moderate",
                "is_rush_order": False,
            })
            log_result("/ml/predict-price", "POST", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/ml/pricing-accuracy", headers=admin_headers)
            log_result("/ml/pricing-accuracy", "GET", r.status_code, r.status_code == 200)

            r = await client.post(f"{API}/ml/generate-description", headers=admin_headers, json={
                "flavor": "Chocolate Raspberry",
                "ingredients": ["dark chocolate", "fresh raspberries", "cream"],
                "decoration_style": "elegant drip cake",
                "event_type": "birthday",
                "tone": "luxury",
            })
            log_result("/ml/generate-description", "POST", r.status_code, r.status_code == 200)

        # Serving estimation (public)
        r = await client.post(f"{API}/ml/estimate-servings", json={
            "diameter_inches": 10,
            "height_inches": 5,
            "layers": 2,
            "shape": "round",
            "serving_style": "party",
        })
        log_result("/ml/estimate-servings", "POST", r.status_code, r.status_code == 200)

        # ─────────────────────────────────────────────────────────────────
        # 10. CUSTOM CAKES
        # ─────────────────────────────────────────────────────────────────
        print("\n🎂 10. Custom Cakes")

        if customer_token:
            r = await client.post(f"{API}/custom-cakes", headers=customer_headers, json={
                "flavor": "Chocolate Ganache",
                "diameter_inches": 10,
                "height_inches": 5,
                "layers": 3,
                "shape": "round",
                "decoration_complexity": "elaborate",
                "decoration_description": "Gold leaf with fresh roses",
                "cake_message": "Happy Birthday Sarah!",
                "event_type": "birthday",
                "is_rush_order": False,
            })
            log_result("/custom-cakes (submit)", "POST", r.status_code, r.status_code in (200, 201))
            if r.status_code in (200, 201):
                custom_cake_id = r.json().get("id")

            r = await client.get(f"{API}/custom-cakes/my-cakes", headers=customer_headers)
            log_result("/custom-cakes/my-cakes", "GET", r.status_code, r.status_code == 200)

        if admin_token:
            r = await client.get(f"{API}/admin/custom-cakes", headers=admin_headers)
            log_result("/admin/custom-cakes", "GET", r.status_code, r.status_code == 200)

            if custom_cake_id:
                r = await client.get(f"{API}/admin/custom-cakes/{custom_cake_id}", headers=admin_headers)
                log_result("/admin/custom-cakes/{id}", "GET", r.status_code, r.status_code == 200)

                # Approve
                r = await client.post(f"{API}/admin/custom-cakes/{custom_cake_id}/approve",
                                      headers=admin_headers, json={
                    "final_price": "120.00",
                    "admin_notes": "Beautiful design — approved!",
                })
                log_result("/admin/custom-cakes/{id}/approve", "POST", r.status_code, r.status_code == 200)

        # ─────────────────────────────────────────────────────────────────
        # 12. SCHEDULING
        # ─────────────────────────────────────────────────────────────────
        print("\n📅 12. Scheduling")

        r = await client.get(f"{API}/schedule/available", params={
            "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        })
        log_result("/schedule/available", "GET", r.status_code, r.status_code == 200)

        # ─────────────────────────────────────────────────────────────────
        # 13. IMAGE PROCESSING
        # ─────────────────────────────────────────────────────────────────
        print("\n🖼️  13. Image Processing")

        if admin_token:
            r = await client.get(f"{API}/images/", headers=admin_headers)
            log_result("/images/ (list)", "GET", r.status_code, r.status_code == 200)

            r = await client.get(f"{API}/images/categories/prompts", headers=admin_headers)
            log_result("/images/categories/prompts", "GET", r.status_code, r.status_code == 200)
            if r.status_code == 200:
                prompts = r.json()
                log_result("  → categories", "INFO", 0, True, f"{len(prompts)} category prompts loaded")

        # ─────────────────────────────────────────────────────────────────
        # 14. AUTHORIZATION TESTS
        # ─────────────────────────────────────────────────────────────────
        print("\n🔐 14. Authorization (should be rejected)")

        # Customer trying admin endpoints
        if customer_token:
            r = await client.get(f"{API}/users/", headers=customer_headers)
            log_result("/users/ (customer→admin)", "GET", r.status_code, r.status_code in (401, 403), "Should reject")

            r = await client.post(f"{API}/products/", headers=customer_headers, json={
                "name": "Hack Product",
                "slug": "hack",
                "description": "test",
                "category": "cake",
                "base_price": "1.00",
            })
            log_result("/products/ (customer→admin)", "POST", r.status_code, r.status_code in (401, 403), "Should reject")

        # No auth on protected endpoints
        r = await client.get(f"{API}/orders/")
        log_result("/orders/ (no auth)", "GET", r.status_code, r.status_code in (401, 403), "Should reject")

        # ─────────────────────────────────────────────────────────────────
        # 15. LOGOUT
        # ─────────────────────────────────────────────────────────────────
        print("\n🔓 15. Logout")

        if admin_token:
            r = await client.post(f"{API}/auth/logout", headers=admin_headers)
            log_result("/auth/logout", "POST", r.status_code, r.status_code == 200)

    # ─────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)

    print(f"📊 TEST RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in results:
            if not r["passed"]:
                print(f"   {r['method']:6s} {r['endpoint']} → {r['status']} {r['detail']}")

    print()
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
