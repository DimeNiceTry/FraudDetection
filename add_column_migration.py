#!/usr/bin/env python3
"""
Скрипт миграции для добавления колонки completed_at в таблицу transactions.
"""
import logging
import os
import sys
from sqlalchemy import create_engine, text

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

def add_column_to_transactions():
    """
    Добавляет колонку completed_at в таблицу транзакций.
    
    Returns:
        bool: True если операция успешна, False в случае ошибки
    """
    try:
        # Подключаемся к базе данных
        engine = create_engine(DATABASE_URL)
        connection = engine.connect()
        
        # Проверяем, существует ли уже колонка completed_at
        check_column_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='transactions' AND column_name='completed_at'
        """
        result = connection.execute(text(check_column_query))
        column_exists = result.fetchone() is not None
        
        if column_exists:
            logger.info("Колонка completed_at уже существует в таблице transactions")
            connection.close()
            return True
        
        # Добавляем колонку, если она не существует
        add_column_query = """
        ALTER TABLE transactions
        ADD COLUMN completed_at TIMESTAMP
        """
        connection.execute(text(add_column_query))
        connection.commit()
        
        logger.info("Колонка completed_at успешно добавлена в таблицу transactions")
        connection.close()
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении колонки: {e}")
        return False

if __name__ == "__main__":
    success = add_column_to_transactions()
    sys.exit(0 if success else 1) 