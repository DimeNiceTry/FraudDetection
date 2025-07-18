"""
Модель баланса пользователя.
"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from ml_service.models.base.entity import Entity


class Balance(Entity):
    """Модель баланса пользователя."""
    
    user_id = Column(String, ForeignKey("user.id"), unique=True, nullable=False)
    amount = Column(Integer, default=0, nullable=False)
    
    # Отношение к пользователю (один-к-одному)
    user = relationship("User", back_populates="balance")

    def __init__(
        self, 
        user_id: str,
        amount: int = 0,
        id: str = None
    ):
        super().__init__(id)
        self.user_id = user_id
        self.amount = amount

    def top_up(self, amount: int) -> bool:
        """
        Пополнить баланс пользователя.
        
        Args:
            amount: Сумма пополнения в кредитах
            
        Returns:
            True если операция успешна, иначе False
        """
        if amount <= 0:
            return False
        
        self.amount += amount
        self.update()
        return True

    def withdraw(self, amount: int) -> bool:
        """
        Списать с баланса пользователя.
        
        Args:
            amount: Сумма списания в кредитах
            
        Returns:
            True если операция успешна, иначе False
        """
        if amount <= 0 or self.amount < amount:
            return False
        
        self.amount -= amount
        self.update()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать баланс в словарь для сериализации.
        
        Returns:
            Словарь с данными баланса
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 