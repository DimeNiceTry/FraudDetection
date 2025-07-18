"""
Модели пользователя для FastAPI.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    """
    Модель токена авторизации.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Данные внутри токена.
    """
    username: Optional[str] = None

class User(BaseModel):
    """
    Модель пользователя.
    """
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True

class UserInDB(User):
    """
    Модель пользователя с паролем для БД.
    """
    hashed_password: str

class UserCreate(BaseModel):
    """
    Модель для создания пользователя.
    """
    username: str
    email: Optional[str] = None
    password: str 