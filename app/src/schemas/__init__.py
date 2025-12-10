"""Pydantic схемы для API"""
from .auth import UserCreate, UserResponse, Token, TokenData
from .billing import BalanceResponse, DepositRequest, TransactionResponse
from .predict import (
    PredictionRequest,
    PredictionResponse,
    PredictionHistoryItem,
    MLModelResponse,
    TaskResponse,
    TaskStatusResponse,
)
from .web import DashboardResponse, HistoryResponse, HistoryItem, UploadResponse

__all__ = [
    "UserCreate",
    "UserResponse",
    "Token",
    "TokenData",
    "BalanceResponse",
    "DepositRequest",
    "TransactionResponse",
    "PredictionRequest",
    "PredictionResponse",
    "PredictionHistoryItem",
    "MLModelResponse",
    "TaskResponse",
    "TaskStatusResponse",
    "DashboardResponse",
    "HistoryResponse",
    "HistoryItem",
    "UploadResponse",
]