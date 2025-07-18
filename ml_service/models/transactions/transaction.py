"""
Модель транзакции по счету пользователя.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from ml_service.models.base.entity import Entity
from ml_service.models.transactions.transaction_types import TransactionType, TransactionStatus


class Transaction(Entity):
    """Модель транзакции по счету пользователя."""
    
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.COMPLETED)
    description = Column(String, nullable=True)
    related_entity_id = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # Отношение к пользователю (многие-к-одному)
    user = relationship("User", back_populates="transactions")

    def __init__(
        self, 
        user_id: str, 
        amount: int, 
        transaction_type: TransactionType,
        status: TransactionStatus = TransactionStatus.COMPLETED,
        description: str = None,
        related_entity_id: str = None,  # Например, ID задачи ML
        id: str = None
    ):
        super().__init__(id)
        self.user_id = user_id
        self.amount = amount
        self.transaction_type = transaction_type
        self.status = status
        self.description = description
        self.related_entity_id = related_entity_id
        self.completed_at = datetime.now()

    def mark_as_failed(self, error_message: str) -> None:
        """
        Отметить транзакцию как неудачную.
        
        Args:
            error_message: Сообщение об ошибке
        """
        self.status = TransactionStatus.FAILED
        self.description = error_message if not self.description else f"{self.description}; {error_message}"
        self.update()

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать транзакцию в словарь для сериализации.
        
        Returns:
            Словарь с данными транзакции
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'transaction_type': self.transaction_type.value,
            'status': self.status.value,
            'description': self.description,
            'related_entity_id': self.related_entity_id,
            'completed_at': self.completed_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 