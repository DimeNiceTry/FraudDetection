"""
Сервис для работы с пользователями.
"""
import logging
import bcrypt
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ml_service.models.user import User
from ml_service.models.balance import Balance
from app.schemas.users import UserCreate

# Настройка логирования
logger = logging.getLogger(__name__)


def create_user(db: Session, user_data: UserCreate):
    """
    Создает нового пользователя.
    
    Args:
        db: Сессия базы данных
        user_data: Данные для создания пользователя
        
    Returns:
        User: Созданный пользователь
        
    Raises:
        ValueError: Если пользователь с таким именем или email уже существует
    """
    try:
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | 
            (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise ValueError("Пользователь с таким именем уже существует")
            else:
                raise ValueError("Пользователь с таким email уже существует")
        
        # Хешируем пароль
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), salt).decode('utf-8')
        
        # Создаем нового пользователя
        user = User(
            username=user_data.username,
            email=user_data.email or f"{user_data.username}@example.com",
            password=hashed_password
        )
        
        # Добавляем пользователя в базу данных
        db.add(user)
        db.flush()  # Получаем ID пользователя
        
        # Создаем начальный баланс для пользователя
        balance = Balance(user_id=user.id, amount=0)
        db.add(balance)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Создан новый пользователь: {user.username}")
        return user
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Ошибка при создании пользователя: {e}")
        raise ValueError("Ошибка при создании пользователя")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при создании пользователя: {e}")
        raise


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Получает пользователя по имени пользователя.
    
    Args:
        db: Сессия базы данных
        username: Имя пользователя
        
    Returns:
        User или None: Объект пользователя или None, если пользователь не найден
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Получает пользователя по ID.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        
    Returns:
        Объект пользователя или None
    """
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    """
    Получает список пользователей.
    
    Args:
        db: Сессия базы данных
        skip: Количество записей для пропуска
        limit: Максимальное количество возвращаемых записей
        
    Returns:
        List[User]: Список пользователей
    """
    return db.query(User).offset(skip).limit(limit).all()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Аутентифицирует пользователя.
    
    Args:
        db: Сессия базы данных
        username: Имя пользователя
        password: Пароль пользователя
        
    Returns:
        Объект пользователя или None
    """
    user = get_user_by_username(db, username)
    if not user:
        logger.warning(f"Пользователь с именем {username} не найден при попытке входа")
        return None
    
    # Проверяем пароль с помощью метода verify_password
    if not user.verify_password(password):
        logger.warning(f"Неверный пароль для пользователя {username}")
        return None
    
    logger.info(f"Успешная аутентификация пользователя {username}")
    return user 