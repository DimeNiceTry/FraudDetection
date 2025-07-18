"""
Упрощенная ORM модель для предсказаний ML.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

# Создаем базовый класс моделей
Base = declarative_base()

class Prediction(Base):
    """
    Модель предсказания машинного обучения для воркера.
    Упрощенная версия без связей с другими таблицами.
    """
    __tablename__ = "predictions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")
    input_data = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    cost = Column(Float, nullable=False)
    worker_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """
        Преобразует объект модели в словарь.
        """
        result = {
            "prediction_id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "input_data": self.input_data,
            "result": self.result,
            "cost": float(self.cost),
            "worker_id": self.worker_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
        return result 