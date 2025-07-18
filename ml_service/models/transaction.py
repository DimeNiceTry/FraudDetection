"""
ORM модель транзакций.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
from ml_service.models.base import Base

class TransactionType(str, Enum):
    """Типы транзакций"""
    TOPUP = "topup"          # Пополнение баланса
    PAYMENT = "payment"      # Оплата предсказания
    REFUND = "refund"        # Возврат средств
    BONUS = "bonus"          # Бонусные начисления

class TransactionStatus(str, Enum):
    """Статусы транзакций"""
    PENDING = "pending"      # Ожидает обработки
    COMPLETED = "completed"  # Успешно обработана
    FAILED = "failed"        # Обработка не удалась

class Transaction(Base):
    """Модель финансовой транзакции пользователя."""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)  # "topup", "payment", "refund", и т.д.
    status = Column(String(20), default=TransactionStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    description = Column(String(255), nullable=True)  # Описание транзакции
    related_entity_id = Column(String(50), nullable=True)  # ID связанной сущности (например, предсказания)
    
    # Отношение к пользователю
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.type})>" 