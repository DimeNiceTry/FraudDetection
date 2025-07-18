"""
Сервисные функции для работы с балансами и транзакциями.
"""
from sqlalchemy.orm import Session
from ml_service.models import Balance, Transaction, User

def get_user_balance(db: Session, user_id: int) -> Balance:
    """
    Получает баланс пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        
    Returns:
        Объект баланса пользователя
    """
    return db.query(Balance).filter(Balance.user_id == user_id).first()

def top_up_balance(db: Session, user_id: int, amount: float) -> tuple:
    """
    Пополняет баланс пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма пополнения
        
    Returns:
        Кортеж из (предыдущий баланс, текущий баланс, ID транзакции)
    """
    # Получаем текущий баланс
    balance = get_user_balance(db, user_id)
    previous_balance = balance.amount
    
    # Создаем транзакцию
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        type="topup",
        status="completed"
    )
    db.add(transaction)
    db.flush()
    
    # Обновляем баланс
    balance.amount += amount
    db.commit()
    
    return previous_balance, balance.amount, transaction.id

def check_and_decrease_balance(db: Session, user_id: int, amount: float) -> bool:
    """
    Проверяет достаточно ли средств и уменьшает баланс.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма списания
        
    Returns:
        True если операция успешна, иначе False
    """
    # Получаем текущий баланс
    balance = get_user_balance(db, user_id)
    
    # Проверяем достаточно ли средств
    if balance.amount < amount:
        return False
    
    # Создаем транзакцию
    transaction = Transaction(
        user_id=user_id,
        amount=-amount,
        type="payment",
        status="completed"
    )
    db.add(transaction)
    
    # Уменьшаем баланс
    balance.amount -= amount
    db.commit()
    
    return True 