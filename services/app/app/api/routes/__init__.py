"""
Маршруты API.
"""
from app.api.routes.healthcheck import router as healthcheck_router
from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.balance import router as balance_router
from app.api.routes.transactions import router as transactions_router

__all__ = [
    "healthcheck_router",
    "users_router",
    "auth_router",
    "predictions_router",
    "balance_router",
    "transactions_router",
] 