"""
Роутер для работы с моделями
"""
import os
import sys
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Добавляем корень проекта в sys.path для импорта storage
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from storage.db import SessionLocal
from ..services import (
    list_models,
    get_model,
    create_task_from_web,
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


@router.get("/models", response_class=HTMLResponse)
async def models_list(
    request: Request,
    db=Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """Список моделей"""
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
    
    return templates.TemplateResponse(
        "models.html",
        {
            "request": request,
            "current_user": current_user,
            "models": models_data,
        }
    )


@router.post("/models/{model_id}/run", response_class=HTMLResponse)
async def run_model_task(
    request: Request,
    model_id: int,
    db=Depends(get_db),
    total_debt: float = Form(...),
    penalty_amount: float = Form(...),
    days_overdue: int = Form(...),
    payments_ratio: float = Form(...),
    is_physical_person: str = Form("false"),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Запустить задачу на модели
    
    Использует user_id из куки (current_user), если пользователь авторизован.
    Если не авторизован, использует user_id=1 по умолчанию (для демо).
    """
    # Определяем user_id: из куки или по умолчанию
    user_id = current_user.id if current_user else 1
    
    # Валидация входных данных
    if total_debt <= 0:
        raise HTTPException(status_code=400, detail="total_debt должен быть положительным")
    if penalty_amount < 0:
        raise HTTPException(status_code=400, detail="penalty_amount должен быть неотрицательным")
    if days_overdue < 0:
        raise HTTPException(status_code=400, detail="days_overdue должен быть неотрицательным")
    if not (0 <= payments_ratio <= 1):
        raise HTTPException(status_code=400, detail="payments_ratio должен быть от 0 до 1")
    
    # Преобразуем строку в bool
    is_physical = is_physical_person.lower() in ("true", "1", "yes", "да")
    
    input_data = {
        "total_debt": float(total_debt),
        "penalty_amount": float(penalty_amount),
        "days_overdue": int(days_overdue),
        "payments_ratio": float(payments_ratio),
        "is_physical_person": is_physical,
    }
    
    try:
        task = create_task_from_web(
            session=db,
            user_id=user_id,
            model_id=model_id,
            input_data=input_data,
        )
        
        # Перенаправляем на страницу деталей задачи
        return RedirectResponse(url=f"/tasks/{task.id}", status_code=303)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
