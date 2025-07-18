"""
Маршруты для работы с балансом пользователя.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.users import User
from app.schemas.balances import BalanceTopUpRequest, BalanceTopUpResponse
from app.services.balances import get_user_balance, top_up_balance

router = APIRouter(prefix="/balance", tags=["balance"])

@router.get("/")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить текущий баланс пользователя.
    """
    balance = get_user_balance(db, current_user.id)
    return {"balance": balance.amount}

@router.post("/topup", response_model=BalanceTopUpResponse)
async def top_up_user_balance(
    request: BalanceTopUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Пополнить баланс пользователя.
    """
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма пополнения должна быть положительной"
        )
    
    previous_balance, current_balance, transaction_id = top_up_balance(
        db, current_user.id, request.amount
    )
    
    return BalanceTopUpResponse(
        previous_balance=previous_balance,
        current_balance=current_balance,
        transaction_id=transaction_id
    )

@router.get("/debug-tables", response_model=dict)
async def debug_tables(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Диагностический эндпоинт для проверки структуры таблиц.
    """
    import logging
    from sqlalchemy import text, inspect
    logger = logging.getLogger(__name__)
    
    # Получаем информацию о таблицах
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    
    # Получаем информацию о моделях
    from ml_service.models.balance import Balance
    from ml_service.models.transaction import Transaction
    
    balance_tablename = Balance.__tablename__
    transaction_tablename = Transaction.__tablename__
    
    # Проверяем реальные данные в балансе
    user_id = current_user.id
    
    try:
        # Проверяем информацию о таблице баланса
        balance_info = {}
        if balance_tablename in tables:
            balance_info['exists'] = True
            balance_info['columns'] = inspector.get_columns(balance_tablename)
            
            # Проверяем, есть ли запись для текущего пользователя
            result = db.execute(text(f"SELECT * FROM {balance_tablename} WHERE user_id = {user_id}")).fetchone()
            if result:
                balance_info['user_record'] = {col: val for col, val in zip(inspector.get_columns(balance_tablename), result)}
            else:
                balance_info['user_record'] = None
        else:
            balance_info['exists'] = False
        
        # Пробуем обновить баланс текущего пользователя напрямую
        update_result = {}
        try:
            # Проверяем текущий баланс
            user_balance = db.execute(text(f"SELECT amount FROM {balance_tablename} WHERE user_id = {user_id}")).scalar()
            update_result['before'] = user_balance
            
            # Обновляем баланс напрямую через SQL
            db.execute(text(f"UPDATE {balance_tablename} SET amount = amount + 1 WHERE user_id = {user_id}"))
            db.commit()
            
            # Проверяем обновленный баланс
            updated_balance = db.execute(text(f"SELECT amount FROM {balance_tablename} WHERE user_id = {user_id}")).scalar()
            update_result['after'] = updated_balance
            update_result['success'] = True
        except Exception as e:
            update_result['error'] = str(e)
            update_result['success'] = False
            db.rollback()
        
        return {
            "tables": tables,
            "balance_table": {
                "name_from_model": balance_tablename,
                "info": balance_info
            },
            "transaction_table": {
                "name_from_model": transaction_tablename
            },
            "balance_update_test": update_result
        }
    except Exception as e:
        logger.error(f"Ошибка при диагностике таблиц: {e}")
        return {"error": str(e)} 