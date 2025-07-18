"""
Модели Pydantic для API.
"""
from app.models.user import (
    Token, TokenData, User, UserInDB, UserCreate
)
from app.models.prediction import (
    PredictionRequest, PredictionResponse, PredictionHistory
)
from app.models.transaction import (
    BalanceTopUpRequest, BalanceTopUpResponse, BalanceResponse
)

__all__ = [
    "Token", "TokenData", "User", "UserInDB", "UserCreate",
    "PredictionRequest", "PredictionResponse", "PredictionHistory",
    "BalanceTopUpRequest", "BalanceTopUpResponse", "BalanceResponse"
]

"""
Импорт ORM-моделей из общей библиотеки.
"""
# Импортируем модели из ml_service для использования в приложении
from ml_service.models.user import User
from ml_service.models.balance import Balance
from ml_service.models.transaction import Transaction
from ml_service.models import TransactionType, TransactionStatus 