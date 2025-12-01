"""Роутер администратора: управление пользователями"""
import os
import sys
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

sys.path.insert(0, os. path.dirname(os.path.dirname(os.path.dirname(os.path. dirname(os.path. abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import UserDB
from storage.repository import deposit_credits

from ..schemas import DepositRequest
from . auth import get_current_user


router = APIRouter(prefix="/admin", tags=["Admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(current_user: UserDB = Depends(get_current_user)) -> UserDB:
    """Проверка что пользователь — администратор"""
    if current_user. role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/users")
def list_users(
    current_user: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    """Список всех пользователей (только для админов)"""
    users = db.query(UserDB).all()
    return [
        {
            "id": u.id,
            "email": u. email,
            "role": u.role,
            "balance": float(u. billing_account.balance) if u.billing_account else 0,
        }
        for u in users
    ]


@router.post("/deposit/{user_id}")
def admin_deposit(
    user_id: int,
    request: DepositRequest,
    current_user: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    """Пополнить баланс пользователю (только для админов)"""
    target_user = db. query(UserDB). filter(UserDB. id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        tx = deposit_credits(
            db,
            user_id=user_id,
            amount=request. amount,
            description=f"Admin deposit by {current_user. email}",
        )
        return {"message": "Deposit successful", "transaction_id": tx. id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )