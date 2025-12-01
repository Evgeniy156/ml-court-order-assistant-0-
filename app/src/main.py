"""
ML Court Order Assistant - FastAPI REST API

Главный модуль приложения. 
Эндпоинты разнесены по роутерам в папке routers/
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Добавляем корень проекта в sys.path для импорта storage
sys.path.insert(0, os. path.dirname(os.path. dirname(os.path.dirname(os.path. abspath(__file__)))))

from storage. db import SessionLocal, engine, Base
from storage.repository import create_default_ml_models

# Импорт роутеров
from . routers import auth_router, billing_router, predict_router, admin_router


# ============== Lifespan ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация БД при старте и очистка при завершении"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_ml_models(db)
    finally:
        db.close()
    yield


# ============== FastAPI приложение ==============
app = FastAPI(
    title="ML Court Order Assistant",
    description="REST API для системы предсказания судебных приказов",
    version="1.0. 0",
    lifespan=lifespan,
)

# Подключаем роутеры
app. include_router(auth_router)
app.include_router(billing_router)
app.include_router(predict_router)
app. include_router(admin_router)


# ============== Общие эндпоинты ==============
@app.get("/", tags=["General"])
def read_root():
    """Главная страница с описанием возможностей"""
    return {
        "service": "ML Court Order Assistant",
        "description": "Система предсказания пригодности дел для судебного приказа",
        "features": [
            "Регистрация и авторизация пользователей",
            "Пополнение баланса кредитов",
            "ML-предсказания с оплатой кредитами",
            "Просмотр истории транзакций и предсказаний",
        ],
        "docs": "/docs",
    }


@app.get("/health", tags=["General"])
def health_check():
    """Проверка состояния сервиса"""
    return {"status": "healthy"}