"""
Скрипт для инициализации базы данных и создания таблиц.
"""
import logging
import time
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from ml_service.models.base import Base
from ml_service.models.user import User
from ml_service.models.balance import Balance
from ml_service.models.transaction import Transaction
from ml_service.models.prediction import Prediction

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки базы данных из переменных окружения
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Строка подключения к базе данных
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def wait_for_db(retry_count=10, retry_delay=5):
    """
    Ожидает доступности базы данных.
    
    Args:
        retry_count: Количество попыток подключения
        retry_delay: Задержка между попытками в секундах
        
    Returns:
        bool: True если подключение успешно, False в случае ошибки
    """
    for i in range(retry_count):
        try:
            logger.info(f"Пытаемся подключиться к PostgreSQL (попытка {i+1}/{retry_count})...")
            engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres")
            connection = engine.connect()
            connection.close()
            logger.info("Подключение к PostgreSQL успешно установлено")
            return True
        except OperationalError as e:
            logger.warning(f"PostgreSQL недоступен: {e}")
            time.sleep(retry_delay)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False

def create_database():
    """
    Создает базу данных, если она не существует.
    
    Returns:
        bool: True если база данных создана или уже существует, False в случае ошибки
    """
    try:
        # Подключаемся к служебной БД postgres
        engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres")
        connection = engine.connect()
        
        # Проверяем, существует ли база данных
        result = connection.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = result.scalar() == 1
        
        if exists:
            logger.info(f"База данных {DB_NAME} уже существует")
        else:
            # Закрываем все соединения и создаем базу данных
            connection.execute("COMMIT")
            connection.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"База данных {DB_NAME} успешно создана")
        
        connection.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        return False

def create_tables():
    """
    Создает таблицы в базе данных.
    
    Returns:
        bool: True если таблицы созданы успешно, False в случае ошибки
    """
    try:
        # Подключаемся к созданной базе данных
        engine = create_engine(DATABASE_URL)
        
        # Создаем таблицы
        Base.metadata.create_all(engine)
        logger.info("Таблицы успешно созданы")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return False

def init_db():
    """
    Инициализирует базу данных.
    
    Returns:
        bool: True если операция успешна, False в случае ошибки
    """
    # Ожидаем доступности базы данных
    if not wait_for_db():
        return False
    
    # Создаем базу данных
    if not create_database():
        return False
    
    # Создаем таблицы
    if not create_tables():
        return False
    
    logger.info("Инициализация базы данных завершена успешно")
    return True

if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1) 