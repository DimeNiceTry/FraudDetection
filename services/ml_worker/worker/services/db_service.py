"""
Сервис для работы с базой данных.
"""
import logging
import json
import time
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from ml_service.db_config import SessionLocal
from worker.config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

from ml_service.models.predictions import Prediction

logger = logging.getLogger(__name__)

def wait_for_postgres():
    """
    Ожидает доступности PostgreSQL.
    
    Returns:
        bool: True, если подключение успешно, иначе False
    """
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к БД (попытка {retry_count + 1}/{max_retries})...")
            
            # Создаем строку подключения из констант
            db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres"
            engine = create_engine(db_url)
            connection = engine.connect()
            connection.close()
            
            logger.info("Подключение к БД успешно установлено")
            return True
        except Exception as e:
            logger.warning(f"БД недоступна, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к БД после нескольких попыток")
    return False

def update_prediction_result(db: Session, prediction_id: str, result: dict, worker_id: str):
    """
    Обновляет результат предсказания в базе данных, используя ORM.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        result: Результат предсказания (словарь)
        worker_id: ID воркера, выполнившего предсказание
    
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        # Получаем предсказание из БД через ORM
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if not prediction:
            logger.error(f"Предсказание с ID {prediction_id} не найдено")
            return False
        
        # Обновляем данные предсказания
        # Проверяем, если result содержит статус, используем его
        if "status" in result and result["status"] in ["completed", "failed"]:
            prediction.status = result["status"]
            logger.info(f"Установлен статус {result['status']} из результата для предсказания {prediction_id}")
        else:
            # Иначе используем статус по умолчанию - completed
            prediction.status = "completed"
            logger.info(f"Установлен статус 'completed' по умолчанию для предсказания {prediction_id}")
            
        prediction.result = result
        prediction.worker_id = worker_id
        prediction.completed_at = datetime.now()
        
        # Сохраняем изменения
        db.commit()
        logger.info(f"Результат предсказания {prediction_id} успешно обновлен")
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении результата предсказания: {e}")
        return False 