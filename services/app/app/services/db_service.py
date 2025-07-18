"""
Сервис для работы с базой данных.
"""
import os
import logging
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.orm import Session
from ml_service.db_config import SessionLocal
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from app.core.config import settings

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

def get_db_connection():
    """
    Создает соединение с базой данных.
    
    Returns:
        psycopg2.connection: Соединение с базой данных
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка при соединении с БД: {e}")
        raise

def get_db():
    """
    Создает сессию SQLAlchemy для работы с БД через ORM.
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
            
            # Создаем тестовое подключение
            db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres"
            engine = create_engine(db_url)
            connection = engine.connect()
            connection.close()
            
            logger.info("Подключение к PostgreSQL успешно установлено")
            return True
        except OperationalError as e:
            logger.warning(f"PostgreSQL недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
        except Exception as e:
            logger.error(f"Неожиданная ошибка при подключении к PostgreSQL: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False

def create_database():
    """
    Создает базу данных и необходимые таблицы.
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
        
        # Подключаемся к новой базе данных и создаем таблицы
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        cursor = conn.cursor()
        
        # Создаем таблицы
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255),
            password VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            amount DECIMAL(10, 2) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id VARCHAR(36) PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            input_data JSONB NOT NULL,
            result JSONB,
            status VARCHAR(20) DEFAULT 'pending',
            cost DECIMAL(10, 2) DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            amount DECIMAL(10, 2) NOT NULL,
            type VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Создаем тестового пользователя, если его нет
        cursor.execute("SELECT 1 FROM users WHERE username = 'test'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                ("test", "test@example.com", "test")  # Для тестов, в реальном приложении хешировать пароль
            )
            user_id = cursor.fetchone()[0]
            
            # Добавляем баланс для тестового пользователя
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
                (user_id, 100.0)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("База данных и таблицы успешно созданы")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        return False

def init_db():
    """
    Инициализирует базу данных.
    """
    if not wait_for_postgres():
        return False
    
    if not create_database():
        return False
    
    return True 