"""
Базовый абстрактный класс для всех сущностей системы.
"""
from abc import ABC
from datetime import datetime
import uuid
from typing import Dict, Any
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declared_attr

from ml_service.db_config import Base


class Entity(Base):
    """Базовый абстрактный класс для всех сущностей системы."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __init__(self, id: str = None):
        if id:
            self.id = id
        else:
            self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def update(self) -> None:
        """Обновить временную метку последнего изменения."""
        self.updated_at = datetime.now() 