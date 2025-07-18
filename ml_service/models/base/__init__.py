"""
Base models initialization
"""
from sqlalchemy.ext.declarative import declarative_base
from ml_service.models.base.entity import Entity
from ml_service.models.base.user_role import UserRole

# Создаем базовый класс для наших моделей
Base = declarative_base()

__all__ = ["Entity", "UserRole", "Base"] 