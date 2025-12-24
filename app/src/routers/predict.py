"""Роутер ML предсказаний: предсказание, история, модели"""
import os
import sys
import logging
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import UserDB, BillingAccountDB, MLModelDB, PredictionDB, MLTaskDB, TransactionDB
from decimal import Decimal

from ..schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionHistoryItem,
    MLModelResponse,
    TaskResponse,
    TaskStatusResponse,
)
from ..services import calculate_prediction
from ..services.rabbitmq_client import get_rabbitmq_publisher
from .auth import get_current_user

logger = logging.getLogger(__name__)


router = APIRouter(tags=["ML"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict", response_model=TaskResponse)
def predict(
    request: PredictionRequest,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Создать асинхронную ML-задачу для предсказания.
    
    Требует достаточного баланса кредитов.
    При создании задачи списываются кредиты.
    Если не удалось поставить задачу в очередь, кредиты возвращаются через rollback.
    """
    # Получаем ML модель
    model = db.query(MLModelDB).filter(
        MLModelDB.name == "court_order_suitability_v1"
    ).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ML model not found",
        )

    # Проверяем баланс
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == current_user.id
    ).first()

    if not account or float(account.balance) < model.price_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {model.price_credits}, available: {float(account.balance) if account else 0}",
        )

    # Создаем задачу в БД
    task = MLTaskDB(
        user_id=current_user.id,
        model_id=model.id,
        total_debt=request.total_debt,
        penalty_amount=request.penalty_amount,
        days_overdue=request.days_overdue,
        payments_ratio=request.payments_ratio,
        is_physical_person=request.is_physical_person,
        status="pending",
        credits_charged=model.price_credits,
    )
    db.add(task)
    db.flush()  # Получаем task.id без коммита

    # Списываем кредиты вручную (в той же транзакции, без commit)
    account.balance = account.balance - Decimal(str(model.price_credits))
    tx = TransactionDB(
        account_id=account.id,
        amount=Decimal(str(-model.price_credits)),
        type="withdraw",
        description=f"ML task {task.id}: {model.name}",
    )
    db.add(tx)
    db.flush()  # Не коммитим еще

    # Пытаемся отправить задачу в очередь RabbitMQ
    try:
        publisher = get_rabbitmq_publisher()
        task_data = {
            "task_id": task.id,
            "user_id": current_user.id,
            "model_id": model.id,
            "total_debt": float(request.total_debt),
            "penalty_amount": float(request.penalty_amount),
            "days_overdue": request.days_overdue,
            "payments_ratio": float(request.payments_ratio),
            "is_physical_person": request.is_physical_person,
        }
        publisher.publish_task(task.id, task_data)
        
        # Если успешно, коммитим транзакцию
        db.commit()
        logger.info(f"Task {task.id} created and published to queue for user {current_user.id}")
        
        return TaskResponse(
            task_id=task.id,
            status="pending",
            message="Task created and queued for processing",
        )
    except Exception as e:
        # Ошибка при публикации в RabbitMQ - откатываем транзакцию
        # При rollback все изменения (создание задачи и списание кредитов) откатываются
        db.rollback()
        
        logger.warning(
            f"Failed to publish task to queue for user {current_user.id}. "
            f"Transaction rolled back. Error: {e}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to queue task for processing. No credits were charged. Error: {str(e)}",
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
                total_debt=p.total_debt,
                penalty_amount=p.penalty_amount,
                days_overdue=p.days_overdue,
                payments_ratio=p.payments_ratio,
                is_physical_person=p.is_physical_person,
                prediction=p.prediction,
                model_name=model.name if model else "unknown",
                credits_charged=p.credits_charged,
                created_at=p.created_at,
            )
        )
    return result


@router.get("/models", response_model=List[MLModelResponse])
def list_models(db=Depends(get_db)):
    """Получить список доступных ML моделей"""
    models = db.query(MLModelDB).all()
    return [
        MLModelResponse(
            id=m.id,
            name=m.name,
            description=m.description,
            price_credits=m.price_credits,
        )
        for m in models
    ]


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: int,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """Получить статус задачи по ID"""
    task = db.query(MLTaskDB).filter(MLTaskDB.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Проверяем, что задача принадлежит пользователю
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        prediction=float(task.prediction) if task.prediction is not None else None,
        error_message=task.error_message,
        credits_charged=task.credits_charged,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )