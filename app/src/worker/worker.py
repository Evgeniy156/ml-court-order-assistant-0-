"""
Worker для обработки ML-задач из RabbitMQ
"""
import os
import sys
import json
import logging
from typing import Dict, Any

import pika

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import MLTaskDB, MLModelDB, PredictionDB
from storage.repository import refund_credits

# Импорты из app/src
app_src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_src_path not in sys.path:
    sys.path.insert(0, app_src_path)

from app.src.services.prediction import calculate_prediction
from app.src.schemas.predict import PredictionRequest

logger = logging.getLogger(__name__)

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "ml_tasks")


def process_task(task_id: int, task_data: Dict[str, Any]) -> None:
    """
    Обработать ML-задачу.
    
    При ошибке выполнения возвращает кредиты пользователю.
    """
    db = SessionLocal()
    try:
        # Загружаем задачу из БД
        task = db.query(MLTaskDB).filter(MLTaskDB.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in database. Credits were already charged, but task is missing.")
            # Если задача не найдена, но кредиты уже списаны, нужно вернуть их
            # Но у нас нет user_id в этом случае, поэтому просто логируем ошибку
            # В реальной ситуации это не должно происходить, так как задача создается до публикации
            return
        
        # Обновляем статус на "running"
        task.status = "running"
        db.commit()
        db.refresh(task)
        
        logger.info(f"Processing task {task_id} for user {task.user_id}")
        
        # Выполняем предсказание
        try:
            prediction_request = PredictionRequest(
                total_debt=task_data["total_debt"],
                penalty_amount=task_data["penalty_amount"],
                days_overdue=task_data["days_overdue"],
                payments_ratio=task_data["payments_ratio"],
                is_physical_person=task_data["is_physical_person"],
            )
            
            prediction_score = calculate_prediction(prediction_request)
            
            # Сохраняем результат
            task.prediction = prediction_score
            task.status = "done"
            task.error_message = None
            
            # Сохраняем в историю предсказаний
            prediction_record = PredictionDB(
                user_id=task.user_id,
                model_id=task.model_id,
                total_debt=task.total_debt,
                penalty_amount=task.penalty_amount,
                days_overdue=task.days_overdue,
                payments_ratio=task.payments_ratio,
                is_physical_person=task.is_physical_person,
                prediction=prediction_score,
                credits_charged=task.credits_charged,
            )
            db.add(prediction_record)
            db.commit()
            
            logger.info(f"Task {task_id} completed successfully. Prediction: {prediction_score}")
            
        except Exception as e:
            # Ошибка при выполнении задачи - возвращаем кредиты
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            
            # Обновляем статус задачи
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
            
            # Возвращаем кредиты пользователю
            try:
                refund_credits(
                    db,
                    user_id=task.user_id,
                    amount=float(task.credits_charged),
                    description=f"Refund for failed task {task_id}: {str(e)}",
                )
                logger.info(
                    f"Credits refunded for user {task.user_id} after task {task_id} failure. "
                    f"Amount: {task.credits_charged}"
                )
            except Exception as refund_error:
                logger.error(
                    f"Failed to refund credits for user {task.user_id} after task {task_id} failure: {refund_error}",
                    exc_info=True
                )
                # Не поднимаем исключение, чтобы не зациклить обработку
            
    except Exception as e:
        logger.error(f"Unexpected error in process_task for task {task_id}: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def callback(ch, method, properties, body):
    """Callback для обработки сообщений из RabbitMQ"""
    try:
        message = json.loads(body)
        task_id = message.get("task_id")
        task_data = message
        
        if not task_id:
            logger.error(f"Invalid message format: {message}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        
        logger.info(f"Received task {task_id} from queue")
        
        # Обрабатываем задачу
        process_task(task_id, task_data)
        
        # Подтверждаем обработку
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error in callback: {e}", exc_info=True)
        # Отклоняем сообщение без повторной постановки в очередь
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Главная функция worker'а"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting ML task worker...")
    
    # Подключаемся к RabbitMQ
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    
    connection = None
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        
        # Настраиваем QoS для обработки по одной задаче за раз
        channel.basic_qos(prefetch_count=1)
        
        # Подписываемся на очередь
        channel.basic_consume(
            queue=RABBITMQ_QUEUE,
            on_message_callback=callback,
        )
        
        logger.info(f"Worker started. Waiting for messages in queue '{RABBITMQ_QUEUE}'...")
        channel.start_consuming()
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
    finally:
        if connection and not connection.is_closed:
            connection.close()
            logger.info("RabbitMQ connection closed")


if __name__ == "__main__":
    main()

