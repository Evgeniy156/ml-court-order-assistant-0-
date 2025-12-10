"""Схемы для веб-интерфейса"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class DashboardResponse(BaseModel):
    """Данные для дашборда"""
    user_id: int
    email: str
    balance: float
    total_transactions: int
    total_predictions: int
    recent_transactions: List[dict]
    recent_predictions: List[dict]


class HistoryItem(BaseModel):
    """Элемент истории транзакций"""
    id: int
    amount: float
    type: str
    description: Optional[str] = None
    created_at: datetime


class HistoryResponse(BaseModel):
    """История транзакций с пагинацией"""
    items: List[HistoryItem]
    total: int
    page: int
    limit: int
    total_pages: int


class UploadResponse(BaseModel):
    """Ответ при загрузке файла"""
    task_id: int
    message: str
    filename: str
    records_processed: int

