"""
Сервис для работы с транзакциями и балансом пользователя.
"""
import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.db_service import get_db_connection
from ml_service.db_config import SessionLocal
from ml_service.models.transaction import Transaction
from ml_service.models.balance import Balance

# Настройка логирования
logger = logging.getLogger(__name__)

def get_balance(user_id):
    """
    Получает текущий баланс пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        float: Текущий баланс пользователя
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли запись о балансе
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance = cursor.fetchone()
        
        if not balance:
            # Если записи нет, создаем новую
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s) RETURNING amount",
                (user_id, 0.0)
            )
            conn.commit()
            return 0.0
        
        return float(balance[0])
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def top_up_balance(user_id, amount, description="Пополнение баланса"):
    """
    Пополняет баланс пользователя.
    
    Args:
        user_id: ID пользователя
        amount: Сумма пополнения
        description: Описание транзакции
        
    Returns:
        tuple: (previous_balance, current_balance, transaction_id)
    """
    if amount <= 0:
        raise ValueError("Сумма пополнения должна быть положительной")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем текущий баланс
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance_row = cursor.fetchone()
        
        if not balance_row:
            # Если записи нет, создаем новую
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s) RETURNING amount",
                (user_id, 0.0)
            )
            prev_balance = 0.0
        else:
            prev_balance = float(balance_row[0])
        
        # Обновляем баланс
        cursor.execute(
            "UPDATE balances SET amount = amount + %s, updated_at = NOW() WHERE user_id = %s RETURNING amount",
            (amount, user_id)
        )
        current_balance = float(cursor.fetchone()[0])
        
        # Записываем транзакцию
        cursor.execute(
            """
            INSERT INTO transactions 
            (user_id, amount, type, status) 
            VALUES (%s, %s, %s, %s) 
            RETURNING id
            """,
            (user_id, amount, "topup", "completed")
        )
        transaction_id = cursor.fetchone()[0]
        
        conn.commit()
        
        return prev_balance, current_balance, transaction_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Ошибка при пополнении баланса: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def deduct_from_balance(user_id, amount, description="Списание средств", related_entity_id=None):
    """
    Списывает средства с баланса пользователя.
    
    Args:
        user_id: ID пользователя
        amount: Сумма списания
        description: Описание транзакции
        related_entity_id: ID связанной сущности (например, предсказания)
        
    Returns:
        tuple: (previous_balance, current_balance, transaction_id)
        
    Raises:
        ValueError: Если недостаточно средств
    """
    if amount <= 0:
        raise ValueError("Сумма списания должна быть положительной")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем текущий баланс
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance_row = cursor.fetchone()
        
        if not balance_row:
            raise ValueError("Недостаточно средств на балансе")
        
        prev_balance = float(balance_row[0])
        
        # Проверяем, достаточно ли средств
        if prev_balance < amount:
            raise ValueError("Недостаточно средств на балансе")
        
        # Обновляем баланс
        cursor.execute(
            "UPDATE balances SET amount = amount - %s, updated_at = NOW() WHERE user_id = %s RETURNING amount",
            (amount, user_id)
        )
        current_balance = float(cursor.fetchone()[0])
        
        # Записываем транзакцию
        cursor.execute(
            """
            INSERT INTO transactions 
            (user_id, amount, type, status, description, related_entity_id) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            RETURNING id
            """,
            (user_id, amount, "deduction", "completed", description, related_entity_id)
        )
        transaction_id = cursor.fetchone()[0]
        
        conn.commit()
        
        return prev_balance, current_balance, transaction_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Ошибка при списании средств: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def get_user_transactions(user_id, skip=0, limit=10):
    """
    Получает историю транзакций пользователя.
    
    Args:
        user_id: ID пользователя
        skip: Сколько транзакций пропустить
        limit: Максимальное количество транзакций
        
    Returns:
        list: Список транзакций
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем транзакции пользователя
        cursor.execute(
            """
            SELECT id, amount, type, status, created_at, description, related_entity_id
            FROM transactions
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, skip)
        )
        transactions = cursor.fetchall()
        
        # Преобразуем результаты
        result = []
        for t in transactions:
            result.append({
                "id": t[0],
                "amount": float(t[1]),
                "type": t[2],
                "status": t[3],
                "timestamp": t[4],
                "description": t[5],
                "related_entity_id": t[6]
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении истории транзакций: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def get_balance_orm(db: Session, user_id: int) -> float:
    """
    Получает текущий баланс пользователя с использованием ORM.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        
    Returns:
        float: Текущий баланс пользователя
    """
    try:
        # Проверяем, есть ли запись о балансе
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            # Если записи нет, создаем новую
            balance = Balance(user_id=user_id, amount=0.0)
            db.add(balance)
            db.commit()
            return 0.0
        
        return float(balance.amount)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при получении баланса (ORM): {e}")
        raise

def top_up_balance_orm(db: Session, user_id: int, amount: float, description="Пополнение баланса"):
    """
    Пополняет баланс пользователя с использованием ORM.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма пополнения
        description: Описание транзакции
        
    Returns:
        tuple: (previous_balance, current_balance, transaction_id)
    """
    if amount <= 0:
        raise ValueError("Сумма пополнения должна быть положительной")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            # Если записи нет, создаем новую
            balance = Balance(user_id=user_id, amount=0.0)
            db.add(balance)
            db.flush()
            prev_balance = 0.0
        else:
            prev_balance = float(balance.amount)
        
        # Обновляем баланс
        balance.amount += amount
        balance.updated_at = datetime.utcnow()
        current_balance = balance.amount
        
        # Записываем транзакцию
        transaction = Transaction(
            user_id=user_id, 
            amount=amount, 
            type="topup", 
            status="completed",
            description=description
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return prev_balance, current_balance, transaction.id
    
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при пополнении баланса (ORM): {e}")
        raise

def deduct_from_balance_orm(db: Session, user_id: int, amount: float, 
                           description="Списание средств", related_entity_id=None):
    """
    Списывает средства с баланса пользователя с использованием ORM.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма списания
        description: Описание транзакции
        related_entity_id: ID связанной сущности (например, предсказания)
        
    Returns:
        tuple: (previous_balance, current_balance, transaction_id)
        
    Raises:
        ValueError: Если недостаточно средств
    """
    if amount <= 0:
        raise ValueError("Сумма списания должна быть положительной")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            raise ValueError("Недостаточно средств на балансе")
        
        prev_balance = float(balance.amount)
        
        # Проверяем, достаточно ли средств
        if prev_balance < amount:
            raise ValueError("Недостаточно средств на балансе")
        
        # Обновляем баланс
        balance.amount -= amount
        balance.updated_at = datetime.utcnow()
        current_balance = balance.amount
        
        # Записываем транзакцию
        transaction = Transaction(
            user_id=user_id, 
            amount=amount, 
            type="deduction", 
            status="completed",
            description=description,
            related_entity_id=related_entity_id
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return prev_balance, current_balance, transaction.id
    
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при списании средств (ORM): {e}")
        raise

def get_user_transactions_orm(db: Session, user_id: int, skip=0, limit=10):
    """
    Получает историю транзакций пользователя с использованием ORM.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Сколько транзакций пропустить
        limit: Максимальное количество транзакций
        
    Returns:
        list: Список транзакций
    """
    try:
        # Получаем транзакции пользователя
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(
            Transaction.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        # Преобразуем результаты
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "amount": float(t.amount),
                "type": t.type,
                "status": t.status,
                "timestamp": t.created_at,
                "description": t.description,
                "related_entity_id": t.related_entity_id
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении истории транзакций (ORM): {e}")
        raise 