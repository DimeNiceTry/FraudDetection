#!/usr/bin/env python3
"""
Скрипт миграции для добавления недостающих колонок в таблицу transactions.
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

def add_missing_columns():
    """
    Добавляет недостающие колонки в таблицу транзакций.
    
    Returns:
        bool: True если операция успешна, False в случае ошибки
    """
    try:
        # Подключаемся к базе данных
        engine = create_engine(DATABASE_URL)
        
        # Список колонок для добавления
        columns = [
            {"name": "completed_at", "type": "TIMESTAMP"},
            {"name": "description", "type": "VARCHAR(255)"},
            {"name": "related_entity_id", "type": "VARCHAR(50)"}
        ]
        
        with engine.begin() as connection:  # Создаем транзакцию
            for column in columns:
                # Проверяем существование колонки
                check_column_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='transactions' AND column_name=:column_name
                """)
                
                result = connection.execute(check_column_query, {"column_name": column["name"]})
                column_exists = result.fetchone() is not None
                
                if column_exists:
                    logger.info(f"Колонка {column['name']} уже существует в таблице transactions")
                    continue
                
                # Добавляем колонку, если она не существует
                add_column_query = text(f"""
                ALTER TABLE transactions
                ADD COLUMN {column['name']} {column['type']}
                """)
                
                connection.execute(add_column_query)
                logger.info(f"Колонка {column['name']} успешно добавлена в таблицу transactions")
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении колонок: {e}")
        return False

if __name__ == "__main__":
    success = add_missing_columns()
    sys.exit(0 if success else 1) 