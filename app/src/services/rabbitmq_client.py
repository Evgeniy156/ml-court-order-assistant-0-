"""RabbitMQ publisher для отправки задач в очередь"""
import os
import json
import logging
from typing import Dict, Any
import pika

logger = logging.getLogger(__name__)

# Настройки RabbitMQ из переменных окружения
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "ml_tasks")


class RabbitMQPublisher:
    """Класс для публикации задач в RabbitMQ"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = RABBITMQ_QUEUE
    
    def connect(self):
        """Установить соединение с RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Объявляем очередь (создастся, если не существует)
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            logger.info(f"Connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def publish_task(self, task_id: int, task_data: Dict[str, Any]) -> None:
        """
        Отправить задачу в очередь RabbitMQ
        
        Args:
            task_id: ID задачи в БД
            task_data: Данные задачи (user_id, model_id, входные данные и т.д.)
        
        Raises:
            Exception: При ошибке отправки сообщения
        """
        if not self.connection or self.connection.is_closed:
            self.connect()
        
        if not self.channel or self.channel.is_closed:
            raise RuntimeError("RabbitMQ channel is not available")
        
        try:
            message = {
                "task_id": task_id,
                **task_data
            }
            
            self.channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Сохранять сообщения на диск
                ),
            )
            
            logger.info(f"Published task {task_id} to queue {self.queue_name}")
        except Exception as e:
            logger.error(f"Failed to publish task {task_id}: {e}")
            raise
    
    def close(self):
        """Закрыть соединение с RabbitMQ"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")


# Глобальный экземпляр publisher (singleton)
_publisher_instance = None


def get_rabbitmq_publisher() -> RabbitMQPublisher:
    """Получить глобальный экземпляр RabbitMQ publisher"""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = RabbitMQPublisher()
    return _publisher_instance

