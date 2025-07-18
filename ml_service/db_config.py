"""
Конфигурация и инициализация базы данных.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# Настройки базы данных PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Формируем строку подключения
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # проверяет соединение перед использованием
    echo=False,  # установите True для отладки SQL запросов
)

# Создаем базовый класс для наших моделей
Base = declarative_base()

# Создаем фабрику сессий
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем обертку сессии, которая привязана к текущему потоку
SessionLocal = scoped_session(session_factory)

# Функция для получения сессии базы данных
def get_db_session():
    """
    Создает и возвращает новую сессию базы данных.
    
    Yields:
        Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для инициализации базы данных
def init_db():
    """
    Создает все таблицы в базе данных.
    """
    from ml_service.models import Base
    Base.metadata.create_all(bind=engine) 