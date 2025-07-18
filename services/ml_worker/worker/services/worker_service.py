"""
Сервис для управления ML-воркером.
"""
import time
import logging
import pika
import socket
import os
from sqlalchemy.orm import Session

from ml_service.db_config import SessionLocal
from ml_service.models import Prediction
from worker.services.message_processor import process_message
from worker.services.rabbitmq_service import wait_for_rabbitmq
from worker.services.db_service import wait_for_postgres

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
ML_TASK_QUEUE = "ml_tasks"

# Идентификатор воркера
WORKER_ID = os.getenv("WORKER_ID", f"worker-{socket.gethostname()}-{os.getpid()}")

logger = logging.getLogger(__name__)

def create_message_processor(worker_id):
    """
    Создает функцию-обработчик сообщений с фиксированным worker_id.
    
    Args:
        worker_id: Идентификатор ML-воркера
        
    Returns:
        function: Функция для обработки сообщений
    """
    def _process_message(ch, method, properties, body):
        db = SessionLocal()
        try:
            process_message(ch, method, properties, body, worker_id, db)
        finally:
            db.close()
    
    return _process_message

def run_worker():
    """
    Запускает воркера для обработки сообщений из очереди.
    """
    # Ожидаем доступности базы данных
    if not wait_for_postgres():
        logger.error("Не удалось подключиться к базе данных")
        return False
        
    # Ожидаем доступности RabbitMQ
    if not wait_for_rabbitmq():
        logger.error("Не удалось подключиться к RabbitMQ")
        return False
    
    # Ожидаем, чтобы дать время другим сервисам запуститься
    time.sleep(5)
    
    try:
        # Устанавливаем соединение с RabbitMQ
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=ML_TASK_QUEUE, durable=True)
        
        # Настраиваем prefetch (сколько сообщений обрабатывать за раз)
        channel.basic_qos(prefetch_count=1)
        
        # Создаем обработчик сообщений с передачей worker_id
        message_processor = create_message_processor(WORKER_ID)
        
        # Начинаем потреблять сообщения
        channel.basic_consume(queue=ML_TASK_QUEUE, on_message_callback=message_processor)
        
        logger.info(f"ML Worker {WORKER_ID} запущен и ожидает сообщения")
        channel.start_consuming()
        return True
    
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
    
    return False 

def wait_for_services():
    """
    Ожидает доступности всех необходимых сервисов.
    
    Returns:
        bool: True, если все сервисы доступны, иначе False
    """
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к сервисам (попытка {retry_count + 1}/{max_retries})...")
            
            # Проверяем подключение к RabbitMQ
            if not wait_for_rabbitmq():
                raise Exception("RabbitMQ недоступен")
            
            # Проверяем подключение к БД
            if not wait_for_postgres():
                raise Exception("База данных недоступна")
            
            logger.info("Подключение ко всем сервисам успешно установлено")
            return True
        except Exception as e:
            logger.warning(f"Не все сервисы доступны, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться ко всем сервисам после нескольких попыток")
    return False 