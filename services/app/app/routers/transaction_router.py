"""
Маршруты для работы с транзакциями и балансом пользователя.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.models.transaction import BalanceTopUpRequest, BalanceTopUpResponse, BalanceResponse
from app.services.auth_service import get_current_user
from app.services.transaction_service import get_balance, top_up_balance, get_user_transactions
from datetime import datetime

# Настройка роутера
router = APIRouter(tags=["transactions"])

@router.get("/balance")
async def get_user_balance(current_user: User = Depends(get_current_user)):
    """
    Получение баланса пользователя.
    """
    try:
        balance = get_balance(current_user.id)
        return {
            "user_id": current_user.id,
            "balance": balance,
            "last_updated": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/balance/topup", response_model=BalanceTopUpResponse)
async def top_up_user_balance(
    request: BalanceTopUpRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Пополнение баланса пользователя.
    """
    try:
        prev_balance, current_balance, transaction_id = top_up_balance(
            current_user.id, 
            request.amount
        )
        return {
            "previous_balance": prev_balance,
            "current_balance": current_balance,
            "transaction_id": transaction_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions")
async def get_transactions_history(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Получение истории транзакций пользователя.
    """
    try:
        transactions = get_user_transactions(current_user.id, skip, limit)
        return {"transactions": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 