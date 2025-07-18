"""
ORM модель балансов пользователей.
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ml_service.models.base import Base

class Balance(Base):
    """Модель баланса пользователя."""
    __tablename__ = "balances"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Отношение к пользователю
    user = relationship("User", back_populates="balance")
    
    def __repr__(self):
        return f"<Balance(user_id={self.user_id}, amount={self.amount})>" 