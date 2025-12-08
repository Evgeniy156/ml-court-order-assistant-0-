"""
Роутер для работы с задачами
"""
import os
import sys
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Добавляем корень проекта в sys.path для импорта storage
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from storage.db import SessionLocal
from ..services import (
    list_tasks,
    get_task,
    get_user_by_id,
)
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


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_list(
    request: Request,
    db=Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """Список всех задач"""
    tasks = list_tasks(db, limit=100)
    
    # Форматируем задачи для шаблона
    tasks_data = []
    for task in tasks:
        user = get_user_by_id(db, task.user_id)
        tasks_data.append({
            "id": task.id,
            "status": task.status,
            "model_name": task.model.name if task.model else "unknown",
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
            "finished_at": task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else None,
            "user_email": user.email if user else f"user_{task.user_id}",
            "user_id": task.user_id,
        })
    
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "current_user": current_user,
            "tasks": tasks_data,
        }
    )


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(
    request: Request,
    task_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """Детали задачи"""
    task = get_task(db, task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    user = get_user_by_id(db, task.user_id)
    
    # Форматируем данные для шаблона
    task_data = {
        "id": task.id,
        "status": task.status,
        "model_name": task.model.name if task.model else "unknown",
        "model_id": task.model_id,
        "user_email": user.email if user else f"user_{task.user_id}",
        "user_id": task.user_id,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
        "started_at": task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task.started_at else None,
        "completed_at": task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else None,
        "input_data": task.input_data,
        "prediction": float(task.prediction) if task.prediction is not None else None,
        "error_message": task.error_message,
        "credits_charged": task.credits_charged,
    }
    
    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "task": task_data,
        }
    )
