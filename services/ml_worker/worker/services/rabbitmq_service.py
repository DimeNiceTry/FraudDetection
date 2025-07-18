"""
Сервис для работы с RabbitMQ.
"""
import os
import json
import logging
import time
import pika

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки RabbitMQ из переменных окружения
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
ML_TASK_QUEUE = "ml_tasks"
ML_RESULT_QUEUE = "ml_results"

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
    Публикует результат предсказания в очередь результатов RabbitMQ.
    
    Args:
        prediction_id: ID предсказания
        result: Результат предсказания
        
    Returns:
        bool: True если публикация успешна, False в случае ошибки
    """
    try:
        # Подготавливаем сообщение
        message = {
            "prediction_id": prediction_id,
            "result": result,
            "timestamp": time.time()
        }
        
        # Конвертируем сообщение в JSON
        message_json = json.dumps(message)
        
        # Получаем соединение с RabbitMQ
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange='',
            routing_key=ML_RESULT_QUEUE,
            body=message_json,
            properties=pika.BasicProperties(
                delivery_mode=2,  # делаем сообщение постоянным
                content_type='application/json'
            )
        )
        
        # Закрываем соединение
        connection.close()
        logger.info(f"Результат предсказания {prediction_id} отправлен в очередь {ML_RESULT_QUEUE}")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при публикации результата предсказания: {e}")
        return False 