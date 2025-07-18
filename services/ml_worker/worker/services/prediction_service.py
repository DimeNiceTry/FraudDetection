"""
Сервис для работы с предсказаниями.
"""
import logging
import random
import time
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ml_service.models import Prediction

logger = logging.getLogger(__name__)

def validate_data(data: Dict[str, Any]) -> bool:
    """
    Проверяет валидность входных данных для предсказания.
    
    Args:
        data: Входные данные
        
    Returns:
        True если данные валидны
    """
    # Проверяем наличие необходимых полей
    required_fields = ["prediction_id", "user_id", "data"]
    for field in required_fields:
        if field not in data:
            logger.error(f"Отсутствует обязательное поле {field}")
            return False
    
    # Дополнительные проверки можно добавить здесь
    return True

def make_prediction(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет предсказание на основе входных данных.
    
    Args:
        input_data: Входные данные для модели
        
    Returns:
        Результат предсказания
    """
    # Эмулируем задержку работы модели
    time_to_sleep = random.uniform(1.0, 3.0)
    time.sleep(time_to_sleep)
    
    # В реальном приложении здесь будет вызов настоящей ML модели
    # Возвращаем тестовый результат
    return {
        "result": random.uniform(0, 1),
        "confidence": random.uniform(0.7, 0.99),
        "processing_time": time_to_sleep
    }

def update_prediction_result(
    db: Session, 
    prediction_id: str, 
    result: Dict[str, Any], 
    worker_id: str
) -> Optional[Prediction]:
    """
    Обновляет результат предсказания в базе данных.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        result: Результат предсказания
        worker_id: ID воркера, выполнившего предсказание
        
    Returns:
        Обновленный объект предсказания или None
    """
    try:
        # Получаем предсказание по ID
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if not prediction:
            logger.error(f"Предсказание {prediction_id} не найдено")
            return None
        
        # Обновляем запись
        prediction.result = result
        
        # Проверяем, если result содержит статус, используем его
        if "status" in result and result["status"] in ["completed", "failed"]:
            prediction.status = result["status"]
            logger.info(f"Установлен статус {result['status']} из результата для предсказания {prediction_id}")
        else:
            # Иначе используем статус по умолчанию - completed
            prediction.status = "completed"
            logger.info(f"Установлен статус 'completed' по умолчанию для предсказания {prediction_id}")
        
        prediction.completed_at = datetime.utcnow()
        prediction.processed_by = worker_id
        
        db.commit()
        logger.info(f"Результат предсказания {prediction_id} успешно обновлен")
        
        return prediction
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении результата предсказания: {e}")
        return None 