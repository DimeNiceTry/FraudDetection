"""
ORM модель предсказаний.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ml_service.models.base import Base

class Prediction(Base):
    """Модель предсказания ML модели."""
    __tablename__ = "predictions"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_data = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    cost = Column(Float, default=1.0)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    processed_by = Column(String(100), nullable=True)  # ID воркера, обработавшего запрос
    
    # Отношение к пользователю
    user = relationship("User", back_populates="predictions")
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, user_id={self.user_id}, status={self.status})>" 