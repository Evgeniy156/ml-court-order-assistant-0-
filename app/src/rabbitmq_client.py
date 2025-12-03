"""
Модуль для работы с RabbitMQ
Предоставляет Publisher для отправки задач в очередь
"""
import json
import os
import logging
import pika

logger = logging.getLogger(__name__)

# Конфигурация RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "ml_tasks")


class RabbitMQPublisher:
    """Publisher для отправки ML задач в RabbitMQ"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = RABBITMQ_QUEUE
        
    def connect(self):
        """Подключение к RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Объявляем очередь (с автоматическим созданием)
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            logger.info(f"Подключено к RabbitMQ: {RABBITMQ_HOST}:{RABBITMQ_PORT}, очередь: {self.queue_name}")
        except Exception as e:
            logger.error(f"Ошибка подключения к RabbitMQ: {e}")
            raise
    
    def publish_task(self, task_id: int, task_data: dict):
        """
        Отправить задачу в очередь
        
        Args:
            task_id: ID задачи из БД
            task_data: Данные задачи (включая input_data, user_id, model_id)
        """
        if not self.channel:
            self.connect()
        
        message = {
            "task_id": task_id,
            "user_id": task_data["user_id"],
            "model_id": task_data["model_id"],
            "input_data": task_data["input_data"],
        }
        
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # делаем сообщение persistent
                    content_type='application/json',
                )
            )
            logger.info(f"Задача {task_id} отправлена в очередь {self.queue_name}")
        except Exception as e:
            logger.error(f"Ошибка отправки задачи {task_id}: {e}")
            raise
    
    def close(self):
        """Закрыть соединение"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Соединение с RabbitMQ закрыто")


# Глобальный publisher (singleton)
_publisher = None


def get_publisher() -> RabbitMQPublisher:
    """Получить глобальный экземпляр publisher"""
    global _publisher
    if _publisher is None:
        _publisher = RabbitMQPublisher()
        _publisher.connect()
    return _publisher
