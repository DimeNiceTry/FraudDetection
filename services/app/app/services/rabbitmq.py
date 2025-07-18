"""
Сервисные функции для работы с RabbitMQ.
"""
import logging
import json
import time
import pika
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_rabbitmq_connection():
    """
    Создает соединение с RabbitMQ.
    
    Returns:
        Объект соединения с RabbitMQ
    """
    credentials = pika.PlainCredentials(
        settings.RABBITMQ_USER, 
        settings.RABBITMQ_PASS
    )
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        virtual_host=settings.RABBITMQ_VHOST,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)


def wait_for_rabbitmq():
    """
    Ожидает доступности RabbitMQ.
    
    Returns:
        bool: True, если подключение успешно, иначе False
    """
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к RabbitMQ (попытка {retry_count + 1}/{max_retries})...")
            connection = get_rabbitmq_connection()
            logger.info("Подключение к RabbitMQ успешно установлено")
            connection.close()
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к RabbitMQ после нескольких попыток")
    return False


def publish_message(message: Dict[str, Any], queue_name: str = None) -> bool:
    """
    Публикует сообщение в очередь RabbitMQ.
    
    Args:
        message: Сообщение для публикации
        queue_name: Имя очереди
        
    Returns:
        True если сообщение опубликовано успешно
    """
    if queue_name is None:
        queue_name = settings.ML_TASK_QUEUE
        
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # сообщение будет сохранено на диск
            )
        )
        
        # Закрываем соединение
        connection.close()
        
        logger.info(f"Сообщение успешно опубликовано в очередь {queue_name}")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при публикации сообщения в RabbitMQ: {e}")
        return False 