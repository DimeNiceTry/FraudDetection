"""
Pydantic схемы для балансов и транзакций.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class BalanceBase(BaseModel):
    """Базовая схема баланса."""
    amount: float

class Balance(BalanceBase):
    """Схема баланса (для ответов API)."""
    user_id: int
    updated_at: datetime

    class Config:
        orm_mode = True

class BalanceTopUpRequest(BaseModel):
    """Схема запроса на пополнение баланса."""
    amount: float

class BalanceTopUpResponse(BaseModel):
    """Схема ответа на пополнение баланса."""
    previous_balance: float
    current_balance: float
    transaction_id: int

class TransactionBase(BaseModel):
    """Базовая схема транзакции."""
    amount: float
    type: str
    status: str = "pending"

class Transaction(TransactionBase):
    """Схема транзакции (для ответов API)."""
    id: int
    user_id: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class TransactionHistory(BaseModel):
    """Схема истории транзакций."""
    transactions: List[Transaction] 