"""
Инициализация базы данных.
"""
import logging
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.core.config import settings
from app.db.session import SessionLocal, engine
from ml_service.models import Base, User, Balance
from worker.config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

logger = logging.getLogger(__name__)

def wait_for_db():
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
            
            # Используем константы для создания строки подключения
            db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
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

def create_database():
    """
    Создает базу данных, если она не существует.
    
    Returns:
        bool: True, если база данных создана или уже существует
    """
    try:
        # Подключение к postgres для создания новой БД
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверяем, существует ли база данных
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{settings.DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Создаем базу данных {settings.DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {settings.DB_NAME}")
            logger.info(f"База данных {settings.DB_NAME} успешно создана")
        else:
            logger.info(f"База данных {settings.DB_NAME} уже существует")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        return False

def create_tables():
    """
    Создает таблицы в базе данных на основе ORM моделей.
    
    Returns:
        bool: True, если таблицы созданы успешно
    """
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы успешно созданы")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return False

def create_test_user(db: Session):
    """
    Создает тестового пользователя, если его нет.
    
    Args:
        db: Сессия базы данных
    """
    try:
        test_user = db.query(User).filter(User.username == "test").first()
        if not test_user:
            # Создаем тестового пользователя
            test_user = User(
                username="test",
                email="test@example.com",
                password="test",  # В реальном приложении хешировать пароль
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            # Добавляем баланс для тестового пользователя
            test_balance = Balance(
                user_id=test_user.id,
                amount=100.0
            )
            db.add(test_balance)
            db.commit()
            
            logger.info("Тестовый пользователь успешно создан")
        else:
            logger.info("Тестовый пользователь уже существует")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании тестового пользователя: {e}")

def init_db():
    """
    Инициализирует базу данных.
    
    Returns:
        bool: True, если инициализация прошла успешно
    """
    if not wait_for_db():
        return False
    
    if not create_database():
        return False
    
    if not create_tables():
        return False
    
    # Создаем тестового пользователя
    db = SessionLocal()
    try:
        create_test_user(db)
    finally:
        db.close()
    
    return True 