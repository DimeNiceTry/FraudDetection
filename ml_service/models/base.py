"""
Базовые классы и настройки для ORM моделей.
"""
from sqlalchemy.ext.declarative import declarative_base

# Создаем базовый класс для наших моделей
Base = declarative_base() 