"""Роутеры API"""
from .auth import router as auth_router, get_current_user, get_db
from .billing import router as billing_router
from .predict import router as predict_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "billing_router",
    "predict_router",
    "admin_router",
    "get_current_user",
    "get_db",
]