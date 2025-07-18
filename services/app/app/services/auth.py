"""
Сервис для аутентификации и авторизации пользователей.
"""
import logging
import bcrypt
import jwt
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from ml_service.models.user import User
from app.core.config import settings
from app.db.session import get_db

from app.config.settings import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_DELTA

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создает JWT токен доступа.
    
    Args:
        data: Данные для кодирования в токене
        expires_delta: Срок действия токена
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or ACCESS_TOKEN_EXPIRE_DELTA)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Получает текущего аутентифицированного пользователя по токену.
    
    Args:
        token: JWT токен
        db: Сессия базы данных
        
    Returns:
        User: Объект пользователя
        
    Raises:
        HTTPException: Если токен недействителен или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Находим пользователя в базе данных
    user = db.query(User).filter(User.username == username).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись пользователя неактивна"
        )
    
    # Обновляем время последнего входа
    user.record_login()
    db.commit()
    
    return user


async def authenticate_user(username: str, password: str, db: Session):
    """
    Аутентифицирует пользователя по имени пользователя и паролю.
    
    Args:
        username: Имя пользователя
        password: Пароль
        db: Сессия базы данных
        
    Returns:
        User или None: Объект пользователя или None, если аутентификация не удалась
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not user.verify_password(password):
        return None
    return user 