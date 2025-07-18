"""
Компоненты для обеспечения безопасности приложения.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.users import get_user_by_username
from ml_service.models import User

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создает JWT токен доступа для пользователя.
    
    Args:
        data: Данные для включения в токен
        expires_delta: Время жизни токена
        
    Returns:
        Строка с JWT токеном
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Получает текущего пользователя из JWT токена.
    
    Args:
        token: JWT токен
        db: Сессия базы данных
        
    Returns:
        Объект пользователя
        
    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    logger.info(f"Получение пользователя по токену: {token[:10]}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        logger.info(f"Декодирование токена с секретным ключом: {settings.SECRET_KEY[:5]}...")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        logger.info(f"Извлеченное имя пользователя из токена: {username}")
        
        if username is None:
            logger.warning("Имя пользователя отсутствует в токене")
            raise credentials_exception
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка при декодировании JWT: {str(e)}")
        raise credentials_exception
    
    logger.info(f"Поиск пользователя в БД по имени: {username}")
    user = get_user_by_username(db, username=username)
    
    if user is None:
        logger.warning(f"Пользователь {username} не найден в базе данных")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"Пользователь {username} не активен")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не активен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"Успешная аутентификация пользователя: {username}")
    return user 