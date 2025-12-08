"""
Роутер для главной страницы / дашборда
"""
import os
import sys
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Добавляем корень проекта в sys.path для импорта storage
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from storage.db import SessionLocal
from ..services import get_task_stats, get_recent_tasks, list_models
from .auth import get_current_user_from_cookie

router = APIRouter()

# Настройка шаблонов
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db=Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """Главная страница с дашбордом"""
    # Получаем статистику
    stats = get_task_stats(db)
    
    # Получаем последние задачи
    recent_tasks = get_recent_tasks(db, limit=10)
    
    # Получаем модели для формы
    models = list_models(db)
    
    # Форматируем модели для шаблона
    models_data = []
    for model in models:
        models_data.append({
            "id": model.id,
            "name": model.name,
            "description": model.description or "Нет описания",
            "price_credits": model.price_credits,
        })
    
    # Форматируем задачи для шаблона
    tasks_data = []
    for task in recent_tasks:
        tasks_data.append({
            "id": task.id,
            "status": task.status,
            "model_name": task.model.name if task.model else "unknown",
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
            "user_id": task.user_id,
        })
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "recent_tasks": tasks_data,
            "models": models_data,
        }
    )
