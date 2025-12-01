"""Схемы для биллинга и транзакций"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    """Ответ с балансом пользователя"""
    user_id: int
    balance: float


class DepositRequest(BaseModel):
    """Запрос на пополнение баланса"""
    amount: float = Field(..., gt=0, description="Сумма пополнения (> 0)")


class TransactionResponse(BaseModel):
    """Ответ с данными транзакции"""
    id: int
    amount: float
    type: str
    created_at: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True