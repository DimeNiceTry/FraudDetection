"""
Модель транзакции предсказания.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from ml_service.models.base.entity import Entity
from ml_service.models.transactions.transaction_types import TransactionType, TransactionStatus


class Prediction(Entity):
    """Модель транзакции, связанной с предсказанием."""
    
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    model_id = Column(String, ForeignKey("model.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default=TransactionStatus.PENDING.value)
    prediction_id = Column(String, nullable=True)
    input_data = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    completed_at = Column(String, nullable=True)
    
    # Отношения
    user = relationship("User", backref="prediction_transactions")
    model = relationship("Model", backref="prediction_transactions")

    def __init__(
        self,
        user_id: str,
        model_id: str,
        amount: int,
        input_data: Optional[Dict[str, Any]] = None,
        prediction_id: Optional[str] = None,
        id: Optional[str] = None
    ):
        super().__init__(id)
        self.user_id = user_id
        self.model_id = model_id
        self.amount = amount
        self.status = TransactionStatus.PENDING.value
        self.input_data = input_data
        self.prediction_id = prediction_id
        self.completed_at = None

    def mark_as_completed(self, result: Dict[str, Any], prediction_id: str) -> None:
        """
        Отметить транзакцию как успешно завершенную.
        
        Args:
            result: Результат предсказания
            prediction_id: Идентификатор созданного предсказания
        """
        self.status = TransactionStatus.COMPLETED.value
        self.result = result
        self.prediction_id = prediction_id
        self.completed_at = datetime.utcnow().isoformat()
        self.update()

    def mark_as_failed(self, error_message: str) -> None:
        """
        Отметить транзакцию как неудачную.
        
        Args:
            error_message: Сообщение об ошибке
        """
        self.status = TransactionStatus.FAILED.value
        self.error_message = error_message
        self.completed_at = datetime.utcnow().isoformat()
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
            'model_id': self.model_id,
            'amount': self.amount,
            'status': self.status,
            'prediction_id': self.prediction_id,
            'input_data': self.input_data,
            'result': self.result,
            'error_message': self.error_message,
            'completed_at': self.completed_at,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 