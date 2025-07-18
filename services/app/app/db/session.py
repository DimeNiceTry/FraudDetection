"""
Управление сессиями базы данных.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Формируем строку подключения
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Создаем движок базы данных
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Предоставляет сессию базы данных как зависимость.
    
    Yields:
        Session: Сессия для работы с БД
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 