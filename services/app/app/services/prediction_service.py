"""
Сервис для работы с предсказаниями.
"""
import os
import uuid
import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session

from ml_service.db_config import SessionLocal
from app.services.rabbitmq_service import publish_message, ML_TASK_QUEUE
from app.services.transaction_service import deduct_from_balance, deduct_from_balance_orm
from ml_service.models.prediction import Prediction

# Настройка логирования
logger = logging.getLogger(__name__)

# Стоимость предсказания
PREDICTION_COST = float(os.getenv("PREDICTION_COST", "1.0"))

def get_db():
    """
    Создает сессию базы данных.
    
    Yields:
        Session: Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_prediction(user_id, input_data):
    """
    Создает новое предсказание.
    
    Args:
        user_id: ID пользователя
        input_data: Входные данные для предсказания
        
    Returns:
        dict: Информация о созданном предсказании
    """
    db = SessionLocal()
    try:
        # Вызываем ORM версию функции
        prediction_info = create_prediction_orm(db, user_id, input_data)
        return prediction_info
    except Exception as e:
        logger.error(f"Ошибка при создании предсказания: {e}")
        raise
    finally:
        db.close()

def get_prediction(prediction_id, user_id):
    """
    Получает информацию о предсказании.
    
    Args:
        prediction_id: ID предсказания
        user_id: ID пользователя
        
    Returns:
        dict: Информация о предсказании
    """
    db = SessionLocal()
    try:
        # Получаем информацию о предсказании через ORM
        prediction = db.query(Prediction).filter(
            Prediction.id == prediction_id,
            Prediction.user_id == user_id
        ).first()
        
        if not prediction:
            raise ValueError("Предсказание не найдено или у вас нет доступа к нему")
        
        # Формируем ответ
        result = {
            "prediction_id": prediction.id,
            "status": prediction.status,
            "result": prediction.result,
            "timestamp": prediction.created_at,
            "completed_at": prediction.completed_at,
            "cost": float(prediction.cost)
        }
        
        return result
    
    except ValueError as e:
        logger.warning(str(e))
        raise
    
    except Exception as e:
        logger.error(f"Ошибка при получении предсказания: {e}")
        raise
    
    finally:
        db.close()

def get_user_predictions(user_id, skip=0, limit=10):
    """
    Получает список предсказаний пользователя.
    
    Args:
        user_id: ID пользователя
        skip: Количество записей для пропуска
        limit: Количество записей для возврата
        
    Returns:
        list: Список предсказаний
    """
    db = SessionLocal()
    try:
        # Получаем список предсказаний через ORM
        predictions = db.query(Prediction).filter(
            Prediction.user_id == user_id
        ).order_by(
            Prediction.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        # Формируем ответ
        results = []
        for pred in predictions:
            results.append({
                "prediction_id": pred.id,
                "status": pred.status,
                "result": pred.result,
                "timestamp": pred.created_at,
                "completed_at": pred.completed_at,
                "cost": float(pred.cost)
            })
        
        return results
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка предсказаний: {e}")
        raise
    
    finally:
        db.close()

def create_prediction_orm(db: Session, user_id: str, input_data: dict):
    """
    Создает новое предсказание с использованием ORM.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        input_data: Входные данные для предсказания
        
    Returns:
        dict: Информация о созданном предсказании
    """
    try:
        # Проверяем наличие данных транзакции
        if "transaction" not in input_data:
            raise ValueError("В данных отсутствует транзакция для анализа")
            
        # Генерируем уникальный ID для предсказания
        prediction_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Списываем средства с баланса пользователя с использованием ORM
        transaction_info = deduct_from_balance_orm(
            db,
            user_id, 
            PREDICTION_COST, 
            f"Оплата анализа транзакции #{prediction_id}", 
            prediction_id
        )
        
        # Создаем новый объект Prediction
        prediction = Prediction(
            id=prediction_id,
            user_id=user_id,
            input_data=input_data,
            status="pending",
            cost=PREDICTION_COST,
            created_at=now
        )
        
        # Добавляем и сохраняем в БД
        db.add(prediction)
        db.commit()
        
        # Отправляем задачу в очередь
        message = {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "data": input_data,
            "timestamp": now.isoformat()
        }
        
        if not publish_message(message, ML_TASK_QUEUE):
            # В случае ошибки отправки задачи отменяем транзакцию
            db.rollback()
            logger.error(f"Не удалось отправить задачу в очередь для предсказания {prediction_id}")
            raise Exception("Ошибка при отправке задачи в очередь обработки")
        
        # Возвращаем информацию о предсказании
        return {
            "prediction_id": prediction_id,
            "status": "pending",
            "timestamp": now,
            "cost": PREDICTION_COST
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании предсказания (ORM): {e}")
        raise 