"""
Сервис для работы с предсказаниями ML.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config.settings import PREDICTION_COST
from app.services.rabbitmq import publish_message
from app.core.config import settings
from app.services.transactions import deduct_from_balance
from ml_service.models.prediction import Prediction

# Настройка логирования
logger = logging.getLogger(__name__)


def create_prediction(db: Session, user_id: int, data: Dict[str, Any], cost: float = 1.0) -> Prediction:
    """
    Создает новую запись предсказания.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        data: Входные данные для предсказания
        cost: Стоимость предсказания
        
    Returns:
        Объект предсказания
    """
    prediction_id = str(uuid.uuid4())
    prediction = Prediction(
        id=prediction_id,
        user_id=user_id,
        input_data=data,
        status="pending",
        cost=cost
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def get_prediction_by_id(db: Session, prediction_id: str) -> Optional[Prediction]:
    """
    Получает предсказание по ID.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        
    Returns:
        Объект предсказания или None
    """
    return db.query(Prediction).filter(Prediction.id == prediction_id).first()


def get_user_predictions(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Prediction]:
    """
    Получает список предсказаний пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Смещение для пагинации
        limit: Ограничение количества результатов
        
    Returns:
        Список объектов предсказаний
    """
    return db.query(Prediction).filter(
        Prediction.user_id == user_id
    ).order_by(
        Prediction.created_at.desc()
    ).offset(skip).limit(limit).all()


def update_prediction_result(
    db: Session, 
    prediction_id: str, 
    result: Dict[str, Any], 
    worker_id: str
) -> Optional[Prediction]:
    """
    Обновляет результат предсказания.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        result: Результат предсказания
        worker_id: ID воркера, выполнившего предсказание
        
    Returns:
        Обновленный объект предсказания или None
    """
    try:
        prediction = get_prediction_by_id(db, prediction_id)
        if not prediction:
            logger.error(f"Предсказание {prediction_id} не найдено")
            return None
            
        prediction.result = result
        
        # Проверяем, если result содержит статус, используем его
        original_status = prediction.status
        need_status_update = False
        
        # Проверка по критериям возврата кредитов
        is_failed = False
        
        # Критерий 1: Статус предсказания равен failed или error
        if "status" in result and result["status"] in ["failed", "error"]:
            is_failed = True
            logger.info(f"Статус {result['status']} в результате для предсказания {prediction_id}")
            
        # Критерий 2: В результате присутствует поле error
        elif "error" in result:
            is_failed = True
            logger.info(f"Предсказание {prediction_id} содержит ошибку: {result.get('error')}")
            
        # Критерий 3: Количество обнаруженных лиц равно 0
        elif result.get("faces_count", 0) == 0:
            is_failed = True
            logger.info(f"Предсказание {prediction_id} с нулевым количеством лиц")
            
        # Критерий 4: Проверка текстового сообщения о ненайденных лицах
        elif any(phrase in str(result.get("prediction", "")).lower() for phrase in 
                ["лица не обнаружены", "лицо не обнаружено", "no face detected", "face not found", "no faces found"]):
            is_failed = True
            logger.info(f"Предсказание {prediction_id} содержит сообщение о ненайденных лицах")
            
        # Критерий 5: Отсутствие информации об эмоциях при завершённом статусе
        elif "status" in result and result["status"] == "completed" and not result.get("emotions") and not result.get("dominant_emotion"):
            is_failed = True
            logger.info(f"Предсказание {prediction_id} без информации об эмоциях при статусе completed")
        
        # Флаг refund_credits для совместимости
        elif result.get("refund_credits", False):
            is_failed = True
            logger.info(f"Предсказание {prediction_id} имеет флаг refund_credits")
        
        # Устанавливаем статус
        if is_failed:
            prediction.status = "failed"
            need_status_update = True
            logger.info(f"Установлен статус 'failed' для предсказания {prediction_id} (был {original_status})")
        # Если нет критериев для failed и статус pending, устанавливаем completed
        elif prediction.status == "pending":
            prediction.status = "completed"
            need_status_update = True
            logger.info(f"Установлен статус 'completed' по умолчанию для предсказания {prediction_id} (был {original_status})")
        
        prediction.completed_at = datetime.utcnow()
        prediction.processed_by = worker_id
        
        # Фиксируем изменения в базе данных
        db.commit()
        db.refresh(prediction)
        
        # Проверяем, корректно ли обновился статус
        if need_status_update and prediction.status != original_status:
            logger.info(f"Статус успешно обновлен с {original_status} на {prediction.status}")
        else:
            logger.warning(f"Обновление статуса не произошло: было {original_status}, осталось {prediction.status}")
        
        return prediction
    except Exception as e:
        logger.error(f"Ошибка при обновлении результата предсказания: {e}")
        db.rollback()
        return None


def get_prediction(db: Session, prediction_id: str, user_id: str):
    """
    Получает информацию о предсказании.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        user_id: ID пользователя (для проверки доступа)
        
    Returns:
        dict: Информация о предсказании
        
    Raises:
        ValueError: Если предсказание не найдено или не принадлежит пользователю
    """
    # Используем ORM для получения предсказания
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    
    if not prediction:
        raise ValueError("Предсказание не найдено")
    
    # Проверяем, принадлежит ли предсказание пользователю
    if prediction.user_id != user_id:
        raise ValueError("У вас нет доступа к этому предсказанию")
    
    # Форматируем ответ
    return {
        "prediction_id": prediction.id,
        "status": prediction.status,
        "result": prediction.result,
        "timestamp": prediction.created_at,
        "completed_at": prediction.completed_at,
        "cost": float(prediction.cost)
    }


def get_user_predictions_list(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    """
    Получает список предсказаний пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Количество записей для пропуска
        limit: Максимальное количество возвращаемых записей
        
    Returns:
        List[dict]: Список предсказаний
    """
    # Используем ORM для получения списка предсказаний
    predictions_query = db.query(Prediction).filter(
        Prediction.user_id == user_id
    ).order_by(
        Prediction.created_at.desc()
    ).offset(skip).limit(limit)
    
    predictions_list = []
    for prediction in predictions_query:
        # Форматируем ответ
        predictions_list.append({
            "prediction_id": prediction.id,
            "status": prediction.status,
            "result": prediction.result,
            "timestamp": prediction.created_at,
            "completed_at": prediction.completed_at,
            "cost": float(prediction.cost)
        })
    
    return predictions_list 