"""
Инициализация ORM моделей.
"""
from ml_service.models.base import Base
from ml_service.models.user import User
from ml_service.models.balance import Balance 
from ml_service.models.prediction import Prediction
from ml_service.models.transaction import Transaction, TransactionType, TransactionStatus

# Обновляем отношения между моделями
from sqlalchemy.orm import relationship

User.balance = relationship("Balance", back_populates="user", uselist=False)
User.predictions = relationship("Prediction", back_populates="user")
User.transactions = relationship("Transaction", back_populates="user")

__all__ = [
    "Base",
    "User",
    "Balance",
    "Prediction",
    "Transaction",
    "TransactionType",
    "TransactionStatus"
] 