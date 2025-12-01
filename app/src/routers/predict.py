"""Роутер ML предсказаний: предсказание, история, модели"""
import os
import sys
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

sys.path. insert(0, os.path.dirname(os.path.dirname(os.path. dirname(os.path.dirname(os. path. abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import UserDB, BillingAccountDB, MLModelDB, PredictionDB
from storage.repository import withdraw_credits

from ..schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionHistoryItem,
    MLModelResponse,
)
from .. services import calculate_prediction
from . auth import get_current_user


router = APIRouter(tags=["ML"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router. post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Выполнить ML-предсказание. 
    
    Требует достаточного баланса кредитов. 
    При успешном предсказании списываются кредиты. 
    Результат сохраняется в историю. 
    """
    # Получаем ML модель
    model = db.query(MLModelDB).filter(
        MLModelDB. name == "court_order_suitability_v1"
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
            status_code=status. HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits.  Required: {model. price_credits}, available: {float(account.balance) if account else 0}",
        )

    # Выполняем предсказание
    prediction_score = calculate_prediction(request)

    # Списываем кредиты
    try:
        withdraw_credits(
            db,
            user_id=current_user.id,
            amount=model.price_credits,
            description=f"ML prediction: {model.name}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Сохраняем предсказание в историю
    prediction_record = PredictionDB(
        user_id=current_user.id,
        model_id=model.id,
        total_debt=request.total_debt,
        penalty_amount=request. penalty_amount,
        days_overdue=request.days_overdue,
        payments_ratio=request.payments_ratio,
        is_physical_person=request.is_physical_person,
        prediction=prediction_score,
        credits_charged=model.price_credits,
    )
    db.add(prediction_record)
    db.commit()

    return PredictionResponse(
        prediction=prediction_score,
        model_name=model. name,
        credits_charged=model.price_credits,
        message="Prediction completed successfully",
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