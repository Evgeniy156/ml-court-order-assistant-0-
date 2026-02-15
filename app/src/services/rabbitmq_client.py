"""RabbitMQ клиент для публикации ML-задач"""
import os
import json
import logging
from typing import Dict, Any

import pika

logger = logging.getLogger(__name__)

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "ml_tasks")


class RabbitMQPublisher:
    """Класс для публикации задач в RabbitMQ"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self._connect()
    
    def _connect(self):
        """Подключение к RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Объявляем очередь (если не существует)
            self.channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            
            logger.info(f"Connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def publish_task(self, task_id: int, task_data: Dict[str, Any]) -> None:
        """Публикация задачи в очередь"""
        if not self.connection or self.connection.is_closed:
            self._connect()
        
        try:
            message = {
                "task_id": task_id,
                **task_data
            }
            
            self.channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Сделать сообщение персистентным
                ),
            )
            
            logger.info(f"Published task {task_id} to queue {RABBITMQ_QUEUE}")
        except Exception as e:
            logger.error(f"Failed to publish task {task_id}: {e}")
            raise
    
    def close(self):
        """Закрыть соединение"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")


# Singleton экземпляр
_publisher_instance = None


def get_rabbitmq_publisher() -> RabbitMQPublisher:
    """Получить экземпляр RabbitMQPublisher (singleton)"""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = RabbitMQPublisher()
    return _publisher_instance

