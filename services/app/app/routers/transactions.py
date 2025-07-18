"""
Маршруты для работы с балансом и транзакциями.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.transactions import BalanceInfo, BalanceTopUpRequest, BalanceTopUpResponse
from app.services.db import get_db
from app.services.auth import get_current_user
from app.services.transactions import get_balance, top_up_balance, get_user_transactions
from ml_service.models.users.user import User

router = APIRouter(tags=["balance"])


@router.get("/balance", response_model=BalanceInfo)
async def get_user_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение текущего баланса пользователя.
    """
    balance = get_balance(db, current_user.id)
    if not balance:
        raise HTTPException(status_code=404, detail="Баланс не найден")
    
    return {
        "user_id": current_user.id,
        "amount": balance.amount,
        "updated_at": balance.updated_at
    }


@router.post("/balance/topup", response_model=BalanceTopUpResponse)
async def topup_user_balance(
    request: BalanceTopUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Пополнение баланса пользователя.
    """
    try:
        previous_balance, current_balance, transaction_id = top_up_balance(
            db, current_user.id, request.amount
        )
        
        return {
            "previous_balance": previous_balance,
            "current_balance": current_balance,
            "transaction_id": transaction_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions")
async def get_transactions_history(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение истории транзакций пользователя.
    """
    transactions = get_user_transactions(db, current_user.id, skip, limit)
    
    return {
        "transactions": [transaction.to_dict() for transaction in transactions],
        "total": len(transactions)
    } 