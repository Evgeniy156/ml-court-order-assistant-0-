"""Роуты для webapp"""
from .dashboard import router as dashboard_router
from .tasks import router as tasks_router
from .models import router as models_router

__all__ = ["dashboard_router", "tasks_router", "models_router"]
