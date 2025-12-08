"""
ML Court Order Assistant - Web UI
FastAPI приложение с Jinja2 шаблонами
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Добавляем корень проекта в sys.path для импорта storage
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from storage.db import engine, Base
from storage.repository import create_default_ml_models
from storage.db import SessionLocal

# Импорт роутеров
from .routes.dashboard import router as dashboard_router
from .routes.tasks import router as tasks_router
from .routes.models import router as models_router
from .routes.auth import router as auth_router


# ============== Lifespan ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация БД при старте"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_ml_models(db)
    finally:
        db.close()
    yield


# ============== FastAPI приложение ==============
app = FastAPI(
    title="ML Court Order Assistant — Web UI",
    description="Web-интерфейс для системы предсказания судебных приказов",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка шаблонов
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Настройка статических файлов
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Подключаем роутеры
app.include_router(dashboard_router)
app.include_router(tasks_router)
app.include_router(models_router)
app.include_router(auth_router)


# ============== Health check ==============
@app.get("/health")
def health():
    """Проверка состояния сервиса"""
    return {"status": "ok"}
