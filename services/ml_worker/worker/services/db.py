"""
Сервис для работы с базой данных в ML Worker.
"""
import logging
import time
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import psycopg2
from sqlalchemy.exc import OperationalError
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ml_service.models.transaction import Transaction
from ml_service.models.base.entity import Entity
from worker.config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, DATABASE_URL
from ml_service.models.prediction import Prediction
from ml_service.models.balance import Balance
from ml_service.models.user import User

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем движок SQLAlchemy для работы с PostgreSQL
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Возвращает сессию базы данных, закрывая её после использования.
    
    Returns:
        Session: Сессия SQLAlchemy для работы с БД
    """
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e


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
            logger.info(f"Пытаемся подключиться к PostgreSQL (попытка {retry_count + 1}/{max_retries})...")
            
            # Создаем строку подключения из констант
            db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres"
            engine = create_engine(db_url)
            connection = engine.connect()
            connection.close()
            
            logger.info("Подключение к PostgreSQL успешно установлено")
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False


def update_prediction_result(prediction_id, result):
    """
    Обновляет результат предсказания в базе данных.
    
    Args:
        prediction_id: ID предсказания
        result: Результат предсказания
        
    Returns:
        bool: True, если обновление прошло успешно, иначе False
    """
    db = None
    try:
        db = get_db()
        
        # Преобразуем результат в безопасный JSON
        result_json = None
        try:
            if isinstance(result, str):
                try:
                    json.loads(result)  # Проверка валидности
                    result_json = result
                except json.JSONDecodeError:
                    result_json = json.dumps({"raw_text": result})
            else:
                result_json = json.dumps(convert_to_safe_json(result))
        except Exception as e:
            logger.error(f"Ошибка сериализации результата в JSON: {e}")
            result_json = json.dumps({"error": "Ошибка формата результата", "details": str(e)})
        
        # Получаем предсказание из базы данных
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if not prediction:
            logger.error(f"Предсказание с ID {prediction_id} не найдено")
            return False

        # Преобразуем результат из JSON в словарь для проверки статуса
        result_dict = json.loads(result_json) if result_json else {}

        # Обновляем предсказание с использованием ORM
        prediction.result = result_json
        
        # Проверяем статус в результате
        if isinstance(result_dict, dict) and "status" in result_dict and result_dict["status"] in ["completed", "failed"]:
            prediction.status = result_dict["status"]
            logger.info(f"Установлен статус {result_dict['status']} из результата для предсказания {prediction_id}")
        else:
            # По умолчанию статус "completed"
            prediction.status = "completed"
            logger.info(f"Установлен статус 'completed' по умолчанию для предсказания {prediction_id}")
        
        prediction.completed_at = datetime.now()
        
        db.commit()
        logger.info(f"Результат предсказания {prediction_id} сохранен в БД")
        return True
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Ошибка при обновлении результата предсказания: {e}")
        return False
    finally:
        if db:
            db.close()


def convert_to_safe_json(obj):
    """
    Преобразует объект в безопасный для JSON формат.
    
    Args:
        obj: Объект для преобразования
        
    Returns:
        Объект, безопасный для JSON сериализации
    """
    if isinstance(obj, dict):
        return {k: convert_to_safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_safe_json(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Преобразуем неподдерживаемые типы в строки
        return str(obj) 