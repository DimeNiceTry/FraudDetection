"""
Менеджер для работы с транзакциями и балансом.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from ml_service.models.transactions.balance import Balance
from ml_service.models.transactions.transaction import Transaction
from ml_service.models.transactions.transaction_types import TransactionType, TransactionStatus


class TransactionManager:
    """Менеджер для работы с транзакциями и балансом."""
    
    def __init__(self, db_session: Session):
        """
        Инициализация менеджера транзакций.
        
        Args:
            db_session: Сессия базы данных
        """
        self.db = db_session
    
    def get_balance(self, user_id: str) -> Optional[Balance]:
        """
        Получить баланс пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Баланс пользователя или None, если не найден
        """
        return self.db.query(Balance).filter(Balance.user_id == user_id).first()
    
    def top_up_balance(self, user_id: str, amount: int, description: str = None) -> bool:
        """
        Пополнить баланс пользователя.
        
        Args:
            user_id: ID пользователя
            amount: Сумма пополнения
            description: Описание транзакции
            
        Returns:
            True если операция успешна, иначе False
        """
        balance = self.get_balance(user_id)
        if not balance:
            return False
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            description=description
        )
        self.db.add(transaction)
        
        # Пополняем баланс
        result = balance.top_up(amount)
        if not result:
            transaction.mark_as_failed("Ошибка пополнения баланса")
            self.db.commit()
            return False
        
        self.db.commit()
        return True
    
    def withdraw_from_balance(self, user_id: str, amount: int, description: str = None, 
                             related_entity_id: str = None) -> bool:
        """
        Списать с баланса пользователя.
        
        Args:
            user_id: ID пользователя
            amount: Сумма списания
            description: Описание транзакции
            related_entity_id: ID связанной сущности (например, задачи ML)
            
        Returns:
            True если операция успешна, иначе False
        """
        balance = self.get_balance(user_id)
        if not balance:
            return False
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.WITHDRAWAL,
            description=description,
            related_entity_id=related_entity_id
        )
        self.db.add(transaction)
        
        # Списываем с баланса
        result = balance.withdraw(amount)
        if not result:
            transaction.mark_as_failed("Недостаточно средств на балансе")
            self.db.commit()
            return False
        
        self.db.commit()
        return True
    
    def get_transaction_history(self, user_id: str, limit: int = 100, 
                              transaction_type: TransactionType = None) -> List[Transaction]:
        """
        Получить историю транзакций пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество транзакций
            transaction_type: Тип транзакций для фильтрации
            
        Returns:
            Список транзакций
        """
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        return query.order_by(Transaction.created_at.desc()).limit(limit).all()
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        Получить транзакцию по ID.
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            Транзакция или None, если не найдена
        """
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first() 