"""
Сервис для работы с транзакциями.
"""
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ml_service.models.balance import Balance
from ml_service.models.transaction import Transaction
from ml_service.models.transaction import TransactionType, TransactionStatus

# Настройка логирования
logger = logging.getLogger(__name__)


def get_balance(db: Session, user_id: int):
    """
    Получает баланс пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
    
    Returns:
        Balance или None: Объект баланса или None, если баланс не найден
    """
    # Убеждаемся, что user_id имеет тип int
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать user_id '{user_id}' в целое число")
            raise ValueError("Некорректный формат ID пользователя")
    
    return db.query(Balance).filter(Balance.user_id == user_id).first()


def top_up_balance(db: Session, user_id: int, amount: float):
    """
    Пополняет баланс пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма пополнения
        
    Returns:
        tuple: (предыдущий баланс, текущий баланс, ID транзакции)
        
    Raises:
        ValueError: Если сумма пополнения отрицательная или возникла ошибка в БД
    """
    if amount <= 0:
        raise ValueError("Сумма пополнения должна быть положительной")
    
    # Убеждаемся, что user_id имеет тип int
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать user_id '{user_id}' в целое число")
            raise ValueError("Некорректный формат ID пользователя")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            # Если баланс не найден, создаем новый
            balance = Balance(user_id=user_id, amount=0)
            db.add(balance)
            db.flush()
        
        # Запоминаем предыдущий баланс
        previous_balance = balance.amount
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=int(amount * 100),  # Храним в копейках/центах
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=f"Пополнение баланса на {amount}"
        )
        
        db.add(transaction)
        
        # Обновляем баланс
        balance.amount += amount
        
        db.commit()
        db.refresh(balance)
        db.refresh(transaction)
        
        logger.info(f"Баланс пользователя {user_id} пополнен на {amount}")
        return (previous_balance, balance.amount, transaction.id)
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Ошибка при пополнении баланса: {e}")
        raise ValueError("Ошибка при пополнении баланса")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при пополнении баланса: {e}")
        raise


def add_to_balance(db: Session, user_id: int, amount: float, description: str, related_entity_id: str = None):
    """
    Добавляет средства на баланс пользователя (возврат средств).
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма возврата
        description: Описание транзакции
        related_entity_id: ID связанной сущности (например, ID предсказания)
        
    Returns:
        tuple: (предыдущий баланс, текущий баланс, ID транзакции)
        
    Raises:
        ValueError: Если сумма возврата отрицательная или возникла ошибка в БД
    """
    if amount <= 0:
        raise ValueError("Сумма возврата должна быть положительной")
    
    # Убеждаемся, что user_id имеет тип int
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать user_id '{user_id}' в целое число")
            raise ValueError("Некорректный формат ID пользователя")
    
    logger.info(f"Начинаем процесс возврата {amount} кредитов пользователю {user_id}")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            # Если баланс не найден, создаем новый
            logger.info(f"Баланс пользователя {user_id} не найден, создаем новый")
            balance = Balance(user_id=user_id, amount=0)
            db.add(balance)
            db.flush()
        
        # Запоминаем предыдущий баланс
        previous_balance = balance.amount
        logger.info(f"Текущий баланс пользователя {user_id}: {previous_balance}")
        
        # Создаем транзакцию возврата
        transaction = Transaction(
            user_id=user_id,
            amount=int(amount * 100),  # Храним в копейках/центах
            type=TransactionType.REFUND,
            status=TransactionStatus.COMPLETED,
            description=description,
            related_entity_id=related_entity_id
        )
        
        db.add(transaction)
        
        # Обновляем баланс
        balance.amount += amount
        logger.info(f"Увеличиваем баланс с {previous_balance} на {amount}, новый баланс: {balance.amount}")
        
        # Фиксируем изменения в базе данных
        db.commit()
        db.refresh(balance)
        db.refresh(transaction)
        
        # Проверяем, что баланс действительно изменился
        new_balance = balance.amount
        if abs(new_balance - (previous_balance + amount)) > 0.001:  # Учитываем возможные ошибки округления
            logger.warning(f"Баланс не увеличился корректно после возврата: было {previous_balance}, добавили {amount}, стало {new_balance}")
        else:
            logger.info(f"Баланс успешно обновлен с {previous_balance} до {new_balance}")
        
        logger.info(f"Пользователю {user_id} успешно возвращено {amount} кредитов. Новый баланс: {new_balance}, ID транзакции: {transaction.id}")
        return (previous_balance, new_balance, transaction.id)
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Ошибка при возврате средств (IntegrityError): {e}")
        # Попробуем ещё раз с прямым SQL-запросом
        try:
            logger.info(f"Пробуем прямой SQL запрос для обновления баланса пользователя {user_id}")
            # Обновляем баланс через SQL
            db.execute(f"UPDATE balances SET amount = amount + {amount} WHERE user_id = {user_id}")
            # Создаем транзакцию
            transaction = Transaction(
                user_id=user_id,
                amount=int(amount * 100),
                type=TransactionType.REFUND,
                status=TransactionStatus.COMPLETED,
                description=f"{description} (через SQL)",
                related_entity_id=related_entity_id
            )
            db.add(transaction)
            db.commit()
            
            # Проверяем новый баланс
            balance = db.query(Balance).filter(Balance.user_id == user_id).first()
            if balance:
                logger.info(f"Баланс успешно обновлен через SQL. Новый баланс: {balance.amount}")
                return (balance.amount - amount, balance.amount, transaction.id)
            else:
                logger.error(f"Баланс не найден после SQL-обновления")
                raise ValueError("Не удалось найти баланс после SQL-обновления")
        except Exception as sql_error:
            db.rollback()
            logger.error(f"Ошибка при прямом SQL-обновлении: {sql_error}")
            raise ValueError(f"Ошибка при возврате средств через SQL: {sql_error}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при возврате средств: {e}")
        raise


def deduct_from_balance(db: Session, user_id: int, amount: float, description: str, related_entity_id: str = None):
    """
    Списывает средства с баланса пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма списания
        description: Описание транзакции
        related_entity_id: ID связанной сущности (например, ID предсказания)
    
    Returns:
        tuple: (предыдущий баланс, текущий баланс, ID транзакции)
        
    Raises:
        ValueError: Если недостаточно средств или возникла ошибка в БД
    """
    if amount <= 0:
        raise ValueError("Сумма списания должна быть положительной")
    
    # Убеждаемся, что user_id имеет тип int
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать user_id '{user_id}' в целое число")
            raise ValueError("Некорректный формат ID пользователя")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            raise ValueError("Баланс пользователя не найден")
        
        # Проверяем достаточно ли средств
        if balance.amount < amount:
            raise ValueError("Недостаточно средств на балансе")
        
        # Запоминаем предыдущий баланс
        previous_balance = balance.amount
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=int(amount * 100),  # Храним в копейках/центах
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=description,
            related_entity_id=related_entity_id
        )
        
        db.add(transaction)
        
        # Обновляем баланс
        balance.amount -= amount
        
        db.commit()
        db.refresh(balance)
        db.refresh(transaction)
        
        logger.info(f"С баланса пользователя {user_id} списано {amount}")
        return (previous_balance, balance.amount, transaction.id)
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Ошибка при списании с баланса: {e}")
        raise ValueError("Ошибка при списании с баланса")
    
    except ValueError as e:
        db.rollback()
        logger.error(f"Ошибка при списании с баланса: {e}")
        raise
    
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при списании с баланса: {e}")
        raise


def get_user_transactions(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """
    Получает историю транзакций пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Количество записей для пропуска
        limit: Максимальное количество возвращаемых записей
    
    Returns:
        List[Transaction]: Список транзакций
    """
    # Убеждаемся, что user_id имеет тип int
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать user_id '{user_id}' в целое число")
            raise ValueError("Некорректный формат ID пользователя")
    
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(
        Transaction.created_at.desc()
    ).offset(skip).limit(limit).all() 