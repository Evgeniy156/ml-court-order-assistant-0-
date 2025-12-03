"""Роутер ML предсказаний: предсказание, история, модели"""
import os
import sys
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

sys.path. insert(0, os.path.dirname(os.path.dirname(os.path. dirname(os.path.dirname(os. path. abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import UserDB, BillingAccountDB, MLModelDB, PredictionDB, MLTaskDB
from storage.repository import withdraw_credits

from ..schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionHistoryItem,
    MLModelResponse,
)
from .. services import calculate_prediction
from ..rabbitmq_client import get_publisher
from . auth import get_current_user


router = APIRouter(tags=["ML"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Отправить ML-задачу в очередь для обработки воркерами.
    
    Требует достаточного баланса кредитов.
    Кредиты списываются сразу при создании задачи.
    Возвращает task_id для отслеживания статуса.
    """
    # Получаем ML модель
    model = db.query(MLModelDB).filter(
        MLModelDB.name == "court_order_suitability_v1"
    ).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ML модель не найдена",
        )

    # Проверяем баланс
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == current_user.id
    ).first()

    if not account or float(account.balance) < model.price_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно кредитов. Требуется: {model.price_credits}, доступно: {float(account.balance) if account else 0}",
        )

    # Списываем кредиты сразу при создании задачи
    try:
        withdraw_credits(
            db,
            user_id=current_user.id,
            amount=model.price_credits,
            description=f"ML задача: {model.name}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Создаем задачу в БД
    task = MLTaskDB(
        user_id=current_user.id,
        model_id=model.id,
        status="pending",
        input_data={
            "total_debt": float(request.total_debt),
            "penalty_amount": float(request.penalty_amount),
            "days_overdue": request.days_overdue,
            "payments_ratio": float(request.payments_ratio),
            "is_physical_person": request.is_physical_person,
        },
        credits_charged=model.price_credits,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Отправляем задачу в RabbitMQ
    try:
        publisher = get_publisher()
        publisher.publish_task(
            task_id=task.id,
            task_data={
                "user_id": current_user.id,
                "model_id": model.id,
                "input_data": task.input_data,
            }
        )
    except Exception as e:
        # Если не удалось отправить в очередь, помечаем задачу как failed
        task.status = "failed"
        task.error_message = f"Не удалось отправить задачу в очередь: {str(e)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось отправить задачу в очередь: {str(e)}",
        )

    return PredictionResponse(
        task_id=task.id,
        status=task.status,
        model_name=model.name,
        credits_charged=model.price_credits,
        message="Задача отправлена на обработку. Используйте task_id для проверки статуса.",
    )


@router.get("/predictions", response_model=List[PredictionHistoryItem])
def get_predictions_history(
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """Получить историю предсказаний пользователя"""
    predictions = (
        db.query(PredictionDB)
        .filter(PredictionDB.user_id == current_user.id)
        .order_by(PredictionDB.created_at.desc())
        .all()
    )
    
    result = []
    for p in predictions:
        model = db.query(MLModelDB).filter(MLModelDB.id == p.model_id).first()
        result.append(
            PredictionHistoryItem(
                id=p.id,
                total_debt=p. total_debt,
                penalty_amount=p.penalty_amount,
                days_overdue=p. days_overdue,
                payments_ratio=p.payments_ratio,
                is_physical_person=p.is_physical_person,
                prediction=p.prediction,
                model_name=model. name if model else "unknown",
                credits_charged=p.credits_charged,
                created_at=p.created_at,
            )
        )
    return result


@router.get("/models", response_model=List[MLModelResponse])
def list_models(db=Depends(get_db)):
    """Получить список доступных ML моделей"""
    models = db. query(MLModelDB).all()
    return [
        MLModelResponse(
            id=m.id,
            name=m.name,
            description=m.description,
            price_credits=m.price_credits,
        )
        for m in models
    ]


@router.get("/task/{task_id}")
def get_task_status(
    task_id: int,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Получить статус ML-задачи
    
    Возвращает информацию о задаче: статус, результат (если готово), ошибку (если failed)
    """
    task = db.query(MLTaskDB).filter(
        MLTaskDB.id == task_id,
        MLTaskDB.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена",
        )
    
    model = db.query(MLModelDB).filter(MLModelDB.id == task.model_id).first()
    
    result = {
        "task_id": task.id,
        "status": task.status,
        "model_name": model.name if model else "unknown",
        "credits_charged": task.credits_charged,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }
    
    if task.status == "completed":
        result["prediction"] = float(task.prediction) if task.prediction else None
        result["input_data"] = task.input_data
    elif task.status == "failed":
        result["error_message"] = task.error_message
    
    return result