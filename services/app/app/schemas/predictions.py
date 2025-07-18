"""
Pydantic схемы для предсказаний.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, validator
from datetime import datetime


class PredictionRequest(BaseModel):
    """Схема запроса на предсказание."""
    data: Dict[str, Any]
    
    @validator('data')
    def validate_input_data(cls, v):
        """Проверяет, что в данных есть транзакция."""
        if not isinstance(v, dict):
            raise ValueError("Данные должны быть словарем")
            
        if "transaction" not in v:
            raise ValueError("В данных отсутствует транзакция для анализа")
            
        return v


class PredictionResponse(BaseModel):
    """Схема ответа с предсказанием."""
    prediction_id: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    cost: float

    class Config:
        orm_mode = True


class PredictionHistory(BaseModel):
    """Схема истории предсказаний."""
    predictions: List[PredictionResponse] 