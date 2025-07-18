"""
Модели для транзакций и баланса.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BalanceTopUpRequest(BaseModel):
    """
    Запрос на пополнение баланса.
    """
    amount: float

class BalanceTopUpResponse(BaseModel):
    """
    Ответ на запрос пополнения баланса.
    """
    previous_balance: float
    current_balance: float
    transaction_id: int

class BalanceResponse(BaseModel):
    """
    Информация о балансе пользователя.
    """
    user_id: int
    balance: float
    last_updated: datetime 