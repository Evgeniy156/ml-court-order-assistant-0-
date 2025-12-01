"""Роутер биллинга: баланс, пополнение, транзакции"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from storage.db import SessionLocal
from storage. models import BillingAccountDB
from storage.repository import deposit_credits, get_user_transactions, get_user_by_email

from .. schemas import BalanceResponse, DepositRequest, TransactionResponse
from ..services import oauth2_scheme, verify_token


router = APIRouter(tags=["Billing"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router. get("/balance", response_model=BalanceResponse)
def get_balance(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Получить текущий баланс"""
    token_data = verify_token(token)
    user = get_user_by_email(db, token_data. email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing account not found",
        )
    return BalanceResponse(user_id=user. id, balance=float(account.balance))


@router.post("/balance/deposit", response_model=TransactionResponse)
def deposit(
    request: DepositRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Пополнить баланс (эмуляция платежа)"""
    token_data = verify_token(token)
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    try:
        tx = deposit_credits(
            db,
            user_id=user.id,
            amount=request.amount,
            description="Balance top-up via API",
        )
        return TransactionResponse(
            id=tx. id,
            amount=float(tx.amount),
            type=tx.type,
            created_at=tx. created_at,
            description=tx.description,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Получить историю транзакций"""
    token_data = verify_token(token)
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    transactions = get_user_transactions(db, user.id)
    return transactions