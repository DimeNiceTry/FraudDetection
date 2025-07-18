"""
Сервис для работы с RabbitMQ в ML Worker.
"""
import logging
import time
import json
import pika

from worker.config.settings import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, 
    RABBITMQ_PASS, RABBITMQ_VHOST, ML_TASK_QUEUE, ML_RESULT_QUEUE
)

# Настройка логирования
logger = logging.getLogger(__name__)


def get_rabbitmq_connection():
    """
    Создает соединение с RabbitMQ.
    
    Returns:
        pika.BlockingConnection: Соединение с RabbitMQ
    """
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
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


def publish_result(prediction_id, result):
    """
    Публикует результат предсказания в очередь результатов.
    
    Args:
        prediction_id: ID предсказания
        result: Результат предсказания
        
    Returns:
        bool: True, если результат успешно опубликован, иначе False
    """
    connection = None
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Создаем очередь, если она не существует
        channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
        
        # Подготавливаем сообщение
        message = {
            "prediction_id": prediction_id,
            "result": result,
        }
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange='',
            routing_key=ML_RESULT_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Делаем сообщение постоянным
                content_type='application/json'
            )
        )
        
        logger.info(f"Результат предсказания {prediction_id} опубликован в очередь {ML_RESULT_QUEUE}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при публикации результата: {e}")
        return False
    finally:
        if connection:
            connection.close()


def setup_rabbitmq_consumer(callback):
    """
    Настраивает получение сообщений из очереди задач.
    
    Args:
        callback: Функция обратного вызова для обработки сообщений
        
    Returns:
        tuple: (соединение, канал)
    """
    # Создаем соединение и канал
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Создаем очереди, если они не существуют
    channel.queue_declare(queue=ML_TASK_QUEUE, durable=True)
    channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
    
    # Настраиваем получение сообщений
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=ML_TASK_QUEUE,
        on_message_callback=callback
    )
    
    logger.info(f"Настроено получение сообщений из очереди {ML_TASK_QUEUE}")
    return connection, channel 