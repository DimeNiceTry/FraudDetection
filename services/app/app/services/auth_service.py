"""
Сервис для аутентификации и авторизации.
"""
import os
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.services.db_service import get_db_connection
from app.models.user import TokenData, User, UserInDB

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "secret_key_for_jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создает JWT токен.
    
    Args:
        data: Данные для включения в токен
        expires_delta: Время жизни токена
        
    Returns:
        str: Encoded JWT токен
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Получает текущего пользователя из токена.
    
    Args:
        token: JWT токен
        
    Returns:
        User: Объект пользователя
        
    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
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
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password, is_active FROM users WHERE username = %s", (token_data.username,))
        user_row = cursor.fetchone()
        
        if user_row is None:
            raise credentials_exception
        
        user_dict = {
            "id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "is_active": user_row[4],
            "hashed_password": user_row[3]
        }
        user = UserInDB(**user_dict)
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        raise credentials_exception
    finally:
        if conn:
            conn.close()
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь неактивен")
    
    return User(id=user.id, username=user.username, email=user.email, is_active=user.is_active)

def verify_password(plain_password, hashed_password):
    """
    Проверяет соответствие пароля хешу.
    
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хеш пароля
        
    Returns:
        bool: True если пароль соответствует хешу
    """
    # В реальном приложении здесь должна быть проверка хеша
    # Например, с использованием passlib
    # return pwd_context.verify(plain_password, hashed_password)
    return plain_password == hashed_password  # Для демонстрации

def authenticate_user(username: str, password: str):
    """
    Аутентифицирует пользователя.
    
    Args:
        username: Имя пользователя
        password: Пароль
        
    Returns:
        User: Объект пользователя если аутентификация успешна, иначе False
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password, is_active FROM users WHERE username = %s", (username,))
        user_row = cursor.fetchone()
        
        if not user_row:
            return False
        
        user_dict = {
            "id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "is_active": user_row[4],
            "hashed_password": user_row[3]
        }
        user = UserInDB(**user_dict)
        
        if not verify_password(password, user.hashed_password):
            return False
        
        return User(id=user.id, username=user.username, email=user.email, is_active=user.is_active)
    except Exception as e:
        logger.error(f"Ошибка при аутентификации пользователя: {e}")
        return False
    finally:
        if conn:
            conn.close() 