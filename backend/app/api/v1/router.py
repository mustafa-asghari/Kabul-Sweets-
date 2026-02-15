"""
API v1 router — aggregates all v1 route modules.
"""

from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.business import router as business_router
from app.api.v1.health import router as health_router
from app.api.v1.ml import router as ml_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router
from app.api.v1.products import router as products_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(business_router)
api_v1_router.include_router(ml_router)
