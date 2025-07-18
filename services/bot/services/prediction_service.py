"""
Сервис для работы с предсказаниями.
"""
import os
import uuid
import json
import logging
import base64
from datetime import datetime
import asyncio

from .db_service import get_db_connection, get_db_user_id
from .db_service import Session, Balance, Transaction
from .rabbitmq_service import publish_message, ML_TASK_QUEUE

# Настройка логирования
logger = logging.getLogger(__name__)

# Стоимость предсказания
PREDICTION_COST = float(os.getenv("PREDICTION_COST", "1.0"))

async def create_prediction(telegram_id, photo_data):
    """
    Создает новое предсказание на основе фотографии.
    
    Args:
        telegram_id: ID пользователя в Telegram
        photo_data: Данные фотографии в формате base64
        
    Returns:
        str: ID созданного предсказания
    """
    conn = None
    session = None
    try:
        # Получаем внутренний ID пользователя
        db_user_id = await get_db_user_id(telegram_id)
        if not db_user_id:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            raise ValueError("Пользователь не найден. Используйте /start для регистрации.")
        
        logger.info(f"Создание предсказания для пользователя с Telegram ID {telegram_id} (DB_ID: {db_user_id})")
        
        # Генерируем уникальный ID
        prediction_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Подготавливаем сообщение для отправки в RabbitMQ
        message = {
            "prediction_id": prediction_id,
            "user_id": db_user_id,
            "data": {"image": photo_data},
            "timestamp": now.isoformat()
        }
        
        # Проверяем баланс через SQLAlchemy
        session = Session()
        balance = session.query(Balance).filter(Balance.user_id == db_user_id).first()
        
        if not balance or balance.amount < PREDICTION_COST:
            logger.error(f"Недостаточно средств на балансе пользователя {db_user_id}: {balance.amount if balance else 0}")
            raise ValueError("Недостаточно средств на балансе")
        
        # Получаем соединение с БД для старого кода
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Обновляем баланс через SQLAlchemy
        balance.amount -= PREDICTION_COST
        
        # Создаем запись о транзакции через SQLAlchemy
        transaction = Transaction(
            user_id=db_user_id, 
            amount=PREDICTION_COST, 
            type="deduction", 
            status="completed"
        )
        session.add(transaction)
        
        # Создаем запись о предсказании в базе данных
        # Вместо сохранения всего изображения в базе, сохраняем только метаданные
        cursor.execute(
            """
            INSERT INTO predictions 
            (id, user_id, input_data, status, cost, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (prediction_id, db_user_id, json.dumps({"image_processed": True}), "pending", PREDICTION_COST, now)
        )
        
        # Отправляем сообщение в очередь
        if not publish_message(message, ML_TASK_QUEUE):
            conn.rollback()
            session.rollback()
            logger.error(f"Не удалось отправить сообщение в очередь для предсказания {prediction_id}")
            raise Exception("Ошибка при отправке задачи")
        
        # Подтверждаем транзакции
        conn.commit()
        session.commit()
        
        logger.info(f"Предсказание {prediction_id} успешно создано для пользователя {db_user_id}")
        return prediction_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        if session:
            session.rollback()
        logger.error(f"Ошибка при создании предсказания: {e}")
        raise
    
    finally:
        if conn:
            conn.close()
        if session:
            session.close()

async def get_prediction_status(prediction_id):
    """
    Получает статус предсказания.
    
    Args:
        prediction_id: ID предсказания
        
    Returns:
        dict: Информация о предсказании
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, status, result, created_at, completed_at, cost 
            FROM predictions 
            WHERE id = %s
            """,
            (prediction_id,)
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            raise ValueError(f"Предсказание {prediction_id} не найдено")
        
        # Обрабатываем поле result корректно, проверяя его тип и формат
        result_data = None
        if prediction[2]:
            try:
                # Если это строка JSON, пробуем распарсить
                if isinstance(prediction[2], str):
                    result_data = json.loads(prediction[2])
                # Если это уже словарь, используем как есть
                elif isinstance(prediction[2], dict):
                    result_data = prediction[2]
                else:
                    # Для других типов данных создаем словарь с текстовым представлением
                    result_data = {"prediction": str(prediction[2])}
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON для предсказания {prediction_id}: {e}")
                result_data = {"prediction": "Ошибка при обработке результата", "error": str(e)}
        
        # Формируем ответ
        result = {
            "prediction_id": prediction[0],
            "status": prediction[1],
            "result": result_data,
            "created_at": prediction[3],
            "completed_at": prediction[4],
            "cost": float(prediction[5])
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении статуса предсказания: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

async def get_user_predictions(telegram_id, limit=5):
    """
    Получает список предсказаний пользователя.
    
    Args:
        telegram_id: ID пользователя в Telegram
        limit: Максимальное количество предсказаний
        
    Returns:
        list: Список предсказаний
    """
    conn = None
    try:
        # Получаем внутренний ID пользователя
        db_user_id = await get_db_user_id(telegram_id)
        if not db_user_id:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            raise ValueError("Пользователь не найден. Используйте /start для регистрации.")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, status, result, created_at, completed_at, cost 
            FROM predictions 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (db_user_id, limit)
        )
        predictions = cursor.fetchall()
        
        # Формируем результат
        result = []
        for p in predictions:
            # Обрабатываем поле result корректно, проверяя его тип и формат
            result_data = None
            if p[2]:
                try:
                    # Если это строка JSON, пробуем распарсить
                    if isinstance(p[2], str):
                        result_data = json.loads(p[2])
                    # Если это уже словарь, используем как есть
                    elif isinstance(p[2], dict):
                        result_data = p[2]
                    else:
                        # Для других типов данных создаем словарь с текстовым представлением
                        result_data = {"prediction": str(p[2])}
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка декодирования JSON для предсказания {p[0]}: {e}")
                    result_data = {"prediction": "Ошибка при обработке результата", "error": str(e)}
            
            result.append({
                "prediction_id": p[0],
                "status": p[1],
                "result": result_data,
                "created_at": p[3],
                "completed_at": p[4],
                "cost": float(p[5])
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка предсказаний: {e}")
        raise
    
    finally:
        if conn:
            conn.close() 