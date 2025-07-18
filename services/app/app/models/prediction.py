"""
Модели для предсказаний.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class PredictionRequest(BaseModel):
    """
    Запрос на предсказание.
    """
    data: Dict[str, Any]

class PredictionResponse(BaseModel):
    """
    Ответ на запрос предсказания.
    """
    prediction_id: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime
    cost: float
    completed_at: Optional[datetime] = None

class PredictionHistory(BaseModel):
    """
    История предсказаний.
    """
    predictions: List[PredictionResponse] 