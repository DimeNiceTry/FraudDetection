"""
Маршруты для работы с историей транзакций.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from ml_service.models.transaction import Transaction
from app.schemas.transactions import TransactionResponse

# Устанавливаем путь для маршрута
router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("", response_model=List[TransactionResponse])
async def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение истории транзакций текущего пользователя.
    Требует аутентификации.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).all()
    
    return transactions 