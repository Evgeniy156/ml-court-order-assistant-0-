"""
Сервисный слой для webapp
Тонкая обёртка над ядром системы (БД, RabbitMQ)
"""
import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Добавляем корень проекта в sys.path для импорта storage
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
# Добавляем app/src в путь для импорта из src
app_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_src)

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from storage.db import SessionLocal
from storage.models import MLTaskDB, MLModelDB, UserDB, BillingAccountDB
from storage.repository import withdraw_credits, deposit_credits
from src.rabbitmq_client import get_publisher

logger = logging.getLogger(__name__)


def get_db_session():
    """Получить сессию БД"""
    return SessionLocal()


def list_tasks(session: Session, limit: int = 100, offset: int = 0) -> List[MLTaskDB]:
    """Получить список задач"""
    return (
        session.query(MLTaskDB)
        .order_by(desc(MLTaskDB.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_task(session: Session, task_id: int) -> Optional[MLTaskDB]:
    """Получить задачу по ID"""
    return session.query(MLTaskDB).filter(MLTaskDB.id == task_id).first()


def get_task_stats(session: Session) -> Dict[str, Any]:
    """Получить статистику по задачам"""
    total = session.query(func.count(MLTaskDB.id)).scalar() or 0
    
    stats = {
        "total": total,
        "pending": session.query(func.count(MLTaskDB.id)).filter(MLTaskDB.status == "pending").scalar() or 0,
        "processing": session.query(func.count(MLTaskDB.id)).filter(MLTaskDB.status == "processing").scalar() or 0,
        "completed": session.query(func.count(MLTaskDB.id)).filter(MLTaskDB.status == "completed").scalar() or 0,
        "failed": session.query(func.count(MLTaskDB.id)).filter(MLTaskDB.status == "failed").scalar() or 0,
    }
    
    return stats


def get_recent_tasks(session: Session, limit: int = 10) -> List[MLTaskDB]:
    """Получить последние задачи"""
    return (
        session.query(MLTaskDB)
        .order_by(desc(MLTaskDB.created_at))
        .limit(limit)
        .all()
    )


def list_models(session: Session) -> List[MLModelDB]:
    """Получить список моделей"""
    return session.query(MLModelDB).all()


def get_model(session: Session, model_id: int) -> Optional[MLModelDB]:
    """Получить модель по ID"""
    return session.query(MLModelDB).filter(MLModelDB.id == model_id).first()


def create_task_from_web(
    session: Session,
    user_id: int,
    model_id: int,
    input_data: Dict[str, Any],
) -> MLTaskDB:
    """
    Создать ML-задачу и отправить в RabbitMQ
    
    Args:
        session: SQLAlchemy сессия
        user_id: ID пользователя
        model_id: ID модели
        input_data: Входные данные для предсказания
    
    Returns:
        MLTaskDB: Созданная задача
    
    Raises:
        ValueError: Если модель не найдена или недостаточно кредитов
        Exception: Если не удалось отправить в RabbitMQ
    """
    # Получаем модель
    model = get_model(session, model_id)
    if not model:
        raise ValueError(f"Модель {model_id} не найдена")
    
    # Проверяем баланс
    account = session.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == user_id
    ).first()
    
    if not account or float(account.balance) < model.price_credits:
        raise ValueError(
            f"Недостаточно кредитов. Требуется: {model.price_credits}, "
            f"доступно: {float(account.balance) if account else 0}"
        )
    
    # Списываем кредиты
    withdraw_credits(
        session,
        user_id=user_id,
        amount=model.price_credits,
        description=f"ML задача: {model.name}",
    )
    session.commit()  # Коммитим списание кредитов
    
    # Создаем задачу
    task = MLTaskDB(
        user_id=user_id,
        model_id=model_id,
        status="pending",
        input_data=input_data,
        credits_charged=model.price_credits,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    
    # Отправляем в RabbitMQ
    try:
        publisher = get_publisher()
        publisher.publish_task(
            task_id=task.id,
            task_data={
                "user_id": user_id,
                "model_id": model_id,
                "input_data": input_data,
            }
        )
    except Exception as e:
        # Если не удалось отправить, возвращаем кредиты и помечаем задачу как failed
        logger.error(
            f"Ошибка отправки задачи {task.id} в RabbitMQ: {e}. "
            f"Возврат кредитов пользователю {user_id} (amount: {model.price_credits})"
        )
        deposit_credits(
            session,
            user_id=user_id,
            amount=model.price_credits,
            description=f"Возврат кредитов: ошибка отправки задачи {task.id}",
        )
        task.status = "failed"
        task.error_message = f"Не удалось отправить задачу в очередь: {str(e)}"
        session.commit()
        raise Exception(f"Не удалось отправить задачу в очередь: {str(e)}")
    
    return task


def get_user_by_id(session: Session, user_id: int) -> Optional[UserDB]:
    """Получить пользователя по ID"""
    return session.query(UserDB).filter(UserDB.id == user_id).first()
