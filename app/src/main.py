"""
ML Court Order Assistant - FastAPI REST API

Главный модуль приложения. 
Эндпоинты разнесены по роутерам в папке routers/
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Добавляем корень проекта в sys.path для импорта storage
# В Docker контейнере: /app/src/main.py -> /app (WORKDIR), storage в /app/storage
# Локально: app/src/main.py -> корень проекта, storage в корне проекта
_current_file = os.path.abspath(__file__)  # /app/src/main.py или app/src/main.py
_app_dir = os.path.dirname(os.path.dirname(_current_file))  # /app или app

# Определяем корень проекта:
# - В Docker: /app/src/main.py -> /app, storage в /app/storage
# - Локально: app/src/main.py -> app, storage в корне проекта (на уровень выше app/)
# Проверяем, где находится storage
_storage_in_app = os.path.join(_app_dir, 'storage')
_storage_in_parent = os.path.join(os.path.dirname(_app_dir), 'storage') if _app_dir != '/' else None

if os.path.exists(_storage_in_app):
    # Storage найден в app_dir (Docker: /app/storage или локально: app/storage)
    _project_root = _app_dir
elif _storage_in_parent and os.path.exists(_storage_in_parent):
    # Storage найден в родительской директории (локально: корень проекта)
    _project_root = os.path.dirname(_app_dir)
elif _app_dir == '/app':
    # Docker контейнер: /app - это корень проекта
    _project_root = '/app'
else:
    # По умолчанию: локальный запуск, storage должен быть в корне проекта
    _project_root = os.path.dirname(_app_dir) if os.path.basename(_app_dir) == 'app' else _app_dir

# Добавляем корень проекта в sys.path
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Проверяем наличие storage перед импортом
_storage_path = os.path.join(_project_root, 'storage')
if not os.path.exists(_storage_path):
    raise ImportError(
        f"Storage directory not found at {_storage_path}. "
        f"Current file: {_current_file}, App dir: {_app_dir}, Project root: {_project_root}, "
        f"Working dir: {os.getcwd()}, PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}"
    )

import storage.db as db_module
from storage.db import Base
from storage.repository import create_default_ml_models

# Импорт роутеров
from .routers import auth_router, billing_router, predict_router, admin_router, web_router, websocket_router


# ============== Lifespan ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация БД при старте и очистка при завершении"""
    # Используем engine и SessionLocal из модуля динамически,
    # чтобы они обновлялись при изменении DATABASE_URL в тестах
    # Важно: получаем engine и SessionLocal в момент выполнения, а не при импорте
    current_engine = db_module.engine
    current_session_local = db_module.SessionLocal
    
    # Создаем таблицы, если их еще нет
    try:
        Base.metadata.create_all(bind=current_engine)
    except Exception as e:
        # В тестах таблицы могут быть уже созданы, это нормально
        # Но если это другая ошибка, нужно её обработать
        import os
        if "test" not in os.environ.get("DATABASE_URL", "").lower() and "test" not in str(current_engine.url).lower():
            raise
    
    # Создаем дефолтные ML модели
    db = current_session_local()
    try:
        create_default_ml_models(db)
    finally:
        db.close()
    yield


# ============== FastAPI приложение ==============
app = FastAPI(
    title="ML Court Order Assistant",
    description="REST API для системы предсказания судебных приказов",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(predict_router)
app.include_router(admin_router)
app.include_router(web_router)
app.include_router(websocket_router)


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