"""
ML Worker для обработки задач из RabbitMQ

Воркер:
1. Подключается к RabbitMQ
2. Получает задачи из очереди
3. Валидирует входные данные
4. Выполняет ML-предсказание
5. Сохраняет результат в БД
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
import pika

# Добавляем корень проекта в sys.path для импорта storage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.db import SessionLocal
from storage.models import MLTaskDB, MLModelDB, BillingAccountDB, PredictionDB
from services.prediction import calculate_prediction
from schemas.predict import PredictionRequest

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "ml_tasks")

# ID воркера для логирования
WORKER_ID = os.getenv("WORKER_ID", f"worker-{os.getpid()}")


def validate_input_data(input_data: dict) -> tuple[bool, str]:
    """
    Валидация входных данных для ML-предсказания
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Проверяем наличие всех обязательных полей
        required_fields = [
            "total_debt",
            "penalty_amount",
            "days_overdue",
            "payments_ratio",
            "is_physical_person"
        ]
        
        for field in required_fields:
            if field not in input_data:
                return False, f"Отсутствует обязательное поле: {field}"
        
        # Проверяем типы и диапазоны
        if not isinstance(input_data["total_debt"], (int, float)) or input_data["total_debt"] <= 0:
            return False, "total_debt должен быть положительным числом"
        
        if not isinstance(input_data["penalty_amount"], (int, float)) or input_data["penalty_amount"] < 0:
            return False, "penalty_amount должен быть неотрицательным числом"
        
        if not isinstance(input_data["days_overdue"], int) or input_data["days_overdue"] < 0:
            return False, "days_overdue должен быть неотрицательным целым числом"
        
        if not isinstance(input_data["payments_ratio"], (int, float)) or not (0 <= input_data["payments_ratio"] <= 1):
            return False, "payments_ratio должен быть числом от 0 до 1"
        
        if not isinstance(input_data["is_physical_person"], bool):
            return False, "is_physical_person должен быть булевым значением"
        
        return True, ""
    
    except Exception as e:
        return False, f"Ошибка валидации: {str(e)}"


def process_ml_task(task_id: int, message_data: dict):
    """
    Обработка ML задачи
    
    Args:
        task_id: ID задачи в БД
        message_data: Данные из сообщения RabbitMQ
    """
    db = SessionLocal()
    
    try:
        # Получаем задачу из БД
        task = db.query(MLTaskDB).filter(MLTaskDB.id == task_id).first()
        
        if not task:
            logger.error(f"[{WORKER_ID}] Задача {task_id} не найдена в БД")
            return
        
        if task.status != "pending":
            logger.warning(f"[{WORKER_ID}] Задача {task_id} уже обработана (статус: {task.status})")
            return
        
        logger.info(f"[{WORKER_ID}] Начало обработки задачи {task_id}")
        
        # Обновляем статус на "processing"
        task.status = "processing"
        task.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Валидация входных данных
        is_valid, error_msg = validate_input_data(task.input_data)
        if not is_valid:
            logger.error(f"[{WORKER_ID}] Задача {task_id}: ошибка валидации - {error_msg}")
            task.status = "failed"
            task.error_message = f"Ошибка валидации: {error_msg}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return
        
        # Получаем модель
        model = db.query(MLModelDB).filter(MLModelDB.id == task.model_id).first()
        if not model:
            logger.error(f"[{WORKER_ID}] Задача {task_id}: модель {task.model_id} не найдена")
            task.status = "failed"
            task.error_message = "ML модель не найдена"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return
        
        # Создаем объект запроса для предсказания
        try:
            prediction_request = PredictionRequest(**task.input_data)
        except Exception as e:
            logger.error(f"[{WORKER_ID}] Задача {task_id}: ошибка создания запроса - {str(e)}")
            task.status = "failed"
            task.error_message = f"Ошибка формата данных: {str(e)}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return
        
        # Выполняем предсказание
        logger.info(f"[{WORKER_ID}] Задача {task_id}: выполнение предсказания...")
        prediction_score = calculate_prediction(prediction_request)
        logger.info(f"[{WORKER_ID}] Задача {task_id}: результат предсказания = {prediction_score:.4f}")
        
        # Сохраняем результат в задаче
        task.prediction = prediction_score
        task.credits_charged = model.price_credits
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        
        # Сохраняем предсказание в историю
        prediction_record = PredictionDB(
            user_id=task.user_id,
            model_id=task.model_id,
            total_debt=task.input_data["total_debt"],
            penalty_amount=task.input_data["penalty_amount"],
            days_overdue=task.input_data["days_overdue"],
            payments_ratio=task.input_data["payments_ratio"],
            is_physical_person=task.input_data["is_physical_person"],
            prediction=prediction_score,
            credits_charged=model.price_credits,
        )
        db.add(prediction_record)
        
        db.commit()
        logger.info(f"[{WORKER_ID}] Задача {task_id} успешно обработана")
        
    except Exception as e:
        logger.error(f"[{WORKER_ID}] Задача {task_id}: неожиданная ошибка - {str(e)}", exc_info=True)
        try:
            task = db.query(MLTaskDB).filter(MLTaskDB.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = f"Внутренняя ошибка: {str(e)}"
                task.completed_at = datetime.now(timezone.utc)
                db.commit()
        except:
            pass
    finally:
        db.close()


def callback(ch, method, properties, body):
    """
    Callback для обработки сообщений из RabbitMQ
    """
    try:
        message = json.loads(body)
        task_id = message["task_id"]
        
        logger.info(f"[{WORKER_ID}] Получена задача {task_id} из очереди")
        
        # Обрабатываем задачу
        process_ml_task(task_id, message)
        
        # Подтверждаем обработку
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[{WORKER_ID}] Задача {task_id} подтверждена (ack)")
        
    except Exception as e:
        logger.error(f"[{WORKER_ID}] Ошибка обработки сообщения: {e}", exc_info=True)
        # Отклоняем сообщение, чтобы оно вернулось в очередь
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Главная функция воркера"""
    logger.info(f"[{WORKER_ID}] Запуск ML Worker...")
    logger.info(f"[{WORKER_ID}] RabbitMQ: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    logger.info(f"[{WORKER_ID}] Очередь: {RABBITMQ_QUEUE}")
    
    # Ждем пока RabbitMQ запустится (для Docker)
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Подключаемся к RabbitMQ
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Объявляем очередь
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            
            # Устанавливаем prefetch_count=1 для равномерного распределения задач
            channel.basic_qos(prefetch_count=1)
            
            logger.info(f"[{WORKER_ID}] Подключено к RabbitMQ")
            logger.info(f"[{WORKER_ID}] Ожидание задач...")
            
            # Начинаем слушать очередь
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=callback
            )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"[{WORKER_ID}] Не удалось подключиться к RabbitMQ (попытка {attempt + 1}/{max_retries}). Повтор через {retry_delay}с...")
                time.sleep(retry_delay)
            else:
                logger.error(f"[{WORKER_ID}] Не удалось подключиться к RabbitMQ после {max_retries} попыток")
                raise
        except KeyboardInterrupt:
            logger.info(f"[{WORKER_ID}] Получен сигнал остановки")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            break
        except Exception as e:
            logger.error(f"[{WORKER_ID}] Неожиданная ошибка: {e}", exc_info=True)
            if 'connection' in locals() and connection.is_open:
                connection.close()
            raise


if __name__ == "__main__":
    main()
