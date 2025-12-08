"""Схемы для ML предсказаний"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Входные данные для предсказания"""
    total_debt: float = Field(..., gt=0, description="Сумма задолженности")
    penalty_amount: float = Field(..., ge=0, description="Сумма пени")
    days_overdue: int = Field(..., ge=0, description="Дней просрочки")
    payments_ratio: float = Field(..., ge=0, le=1, description="Доля оплаченного (0-1)")
    is_physical_person: bool = Field(..., description="Физическое лицо")


class PredictionResponse(BaseModel):
    """Ответ с результатом предсказания"""
    task_id: Optional[int] = None
    status: str = "pending"
    prediction: Optional[float] = None
    model_name: str
    credits_charged: int
    message: str

    model_config = {"protected_namespaces": ()}


class PredictionHistoryItem(BaseModel):
    """Элемент истории предсказаний"""
    id: int
    total_debt: float
    penalty_amount: float
    days_overdue: int
    payments_ratio: float
    is_physical_person: bool
    prediction: float
    model_name: str
    credits_charged: int
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class MLModelResponse(BaseModel):
    """Информация о ML модели"""
    id: int
    name: str
    description: Optional[str] = None
    price_credits: int