"""Роутер для веб-интерфейса"""
import os
import sys
import csv
import logging
from typing import List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import UserDB, BillingAccountDB, TransactionDB, PredictionDB, MLModelDB, MLTaskDB

from ..schemas.web import DashboardResponse, HistoryResponse, HistoryItem, UploadResponse
from ..schemas.predict import PredictionRequest
from ..services.validation import validate_csv_row, validate_file_size, validate_file_extension
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/web", tags=["Web"])


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить данные для дашборда"""
    # Получаем баланс
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing account not found",
        )
    
    # Подсчитываем транзакции
    total_transactions = db.query(func.count(TransactionDB.id)).join(
        BillingAccountDB, TransactionDB.account_id == BillingAccountDB.id
    ).filter(BillingAccountDB.user_id == current_user.id).scalar() or 0
    
    # Подсчитываем предсказания
    total_predictions = db.query(func.count(PredictionDB.id)).filter(
        PredictionDB.user_id == current_user.id
    ).scalar() or 0
    
    # Последние транзакции (5 штук)
    recent_transactions = (
        db.query(TransactionDB)
        .join(BillingAccountDB, TransactionDB.account_id == BillingAccountDB.id)
        .filter(BillingAccountDB.user_id == current_user.id)
        .order_by(TransactionDB.created_at.desc())
        .limit(5)
        .all()
    )
    
    # Последние предсказания (5 штук)
    recent_predictions = (
        db.query(PredictionDB)
        .filter(PredictionDB.user_id == current_user.id)
        .order_by(PredictionDB.created_at.desc())
        .limit(5)
        .all()
    )
    
    return DashboardResponse(
        user_id=current_user.id,
        email=current_user.email,
        balance=float(account.balance),
        total_transactions=total_transactions,
        total_predictions=total_predictions,
        recent_transactions=[
            {
                "id": tx.id,
                "amount": float(tx.amount),
                "type": tx.type,
                "description": tx.description,
                "created_at": tx.created_at.isoformat(),
            }
            for tx in recent_transactions
        ],
        recent_predictions=[
            {
                "id": p.id,
                "prediction": float(p.prediction),
                "credits_charged": p.credits_charged,
                "created_at": p.created_at.isoformat(),
            }
            for p in recent_predictions
        ],
    )


@router.get("/history", response_model=HistoryResponse)
def get_history(
    page: int = 1,
    limit: int = 20,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить историю транзакций с пагинацией"""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    
    # Получаем аккаунт
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing account not found",
        )
    
    # Подсчитываем общее количество
    total = (
        db.query(func.count(TransactionDB.id))
        .filter(TransactionDB.account_id == account.id)
        .scalar() or 0
    )
    
    # Получаем транзакции с пагинацией
    transactions = (
        db.query(TransactionDB)
        .filter(TransactionDB.account_id == account.id)
        .order_by(TransactionDB.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return HistoryResponse(
        items=[
            HistoryItem(
                id=tx.id,
                amount=float(tx.amount),
                type=tx.type,
                description=tx.description,
                created_at=tx.created_at,
            )
            for tx in transactions
        ],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Загрузить файл CSV для массовых предсказаний"""
    # Валидация файла
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    try:
        validate_file_extension(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Читаем файл
    content = await file.read()
    
    # Валидация размера файла
    try:
        validate_file_size(len(content), max_size_mb=10)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file encoding. Use UTF-8",
        )
    
    # Парсим CSV
    try:
        csv_reader = csv.DictReader(text_content.splitlines())
        records = list(csv_reader)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}",
        )
    
    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty",
        )
    
    # Получаем модель
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
    
    required_credits = len(records) * model.price_credits
    if not account or float(account.balance) < required_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {required_credits}, available: {float(account.balance) if account else 0}",
        )
    
    # Обрабатываем каждую запись
    tasks_created = 0
    from ..services.rabbitmq_client import get_rabbitmq_publisher
    
    try:
        publisher = get_rabbitmq_publisher()
        
        for idx, record in enumerate(records, start=1):
            try:
                # Валидация строки CSV с использованием модуля валидации
                validated_data = validate_csv_row(record, row_number=idx)
                
                # Создаем задачу
                task = MLTaskDB(
                    user_id=current_user.id,
                    model_id=model.id,
                    total_debt=validated_data['total_debt'],
                    penalty_amount=validated_data['penalty_amount'],
                    days_overdue=validated_data['days_overdue'],
                    payments_ratio=validated_data['payments_ratio'],
                    is_physical_person=validated_data['is_physical_person'],
                    status="pending",
                    credits_charged=model.price_credits,
                )
                db.add(task)
                db.flush()
                
                # Списываем кредиты
                account.balance = account.balance - Decimal(str(model.price_credits))
                tx = TransactionDB(
                    account_id=account.id,
                    amount=Decimal(str(-model.price_credits)),
                    type="withdraw",
                    description=f"ML task {task.id}: {model.name} (from CSV)",
                )
                db.add(tx)
                db.flush()
                
                # Публикуем в очередь
                task_data = {
                    "task_id": task.id,
                    "user_id": current_user.id,
                    "model_id": model.id,
                    "total_debt": validated_data['total_debt'],
                    "penalty_amount": validated_data['penalty_amount'],
                    "days_overdue": validated_data['days_overdue'],
                    "payments_ratio": validated_data['payments_ratio'],
                    "is_physical_person": validated_data['is_physical_person'],
                }
                publisher.publish_task(task.id, task_data)
                
                tasks_created += 1
                
            except ValueError as e:
                logger.warning(f"Invalid record in CSV (row {idx}): {record}, error: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing CSV row {idx}: {e}")
                continue
        
        db.commit()
        logger.info(f"Created {tasks_created} tasks from CSV file for user {current_user.id}")
        
        return UploadResponse(
            task_id=tasks_created,  # Возвращаем количество созданных задач
            message=f"Successfully processed {tasks_created} records from CSV",
            filename=file.filename,
            records_processed=tasks_created,
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing CSV file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}",
        )

