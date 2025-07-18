"""
Сервис для работы с базой данных.
"""
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ml_service.db_config import Base
from app.config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, DATABASE_URL

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем движок SQLAlchemy для работы с PostgreSQL
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Возвращает сессию базы данных, закрывая её после использования.
    
    Yields:
        Session: Сессия SQLAlchemy для работы с БД
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
            
            # Создаем временное подключение для проверки
            engine = create_engine(DATABASE_URL)
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


def create_database():
    """
    Создает базу данных, если она не существует.
    
    Returns:
        bool: True, если база данных создана или уже существует, иначе False
    """
    try:
        # Подключение к postgres для создания новой БД
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверяем, существует ли база данных
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Создаем базу данных {DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"База данных {DB_NAME} успешно создана")
        else:
            logger.info(f"База данных {DB_NAME} уже существует")
        
        cursor.close()
        conn.close()
        
        # Создаем схему таблиц
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы успешно созданы")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        return False


def init_db():
    """
    Инициализирует базу данных.
    
    Returns:
        bool: True, если инициализация прошла успешно, иначе False
    """
    if wait_for_postgres():
        return create_database()
    return False 