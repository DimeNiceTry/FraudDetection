"""
Pydantic схемы для пользователей.
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class Token(BaseModel):
    """Схема JWT токена."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Схема данных токена."""
    username: Optional[str] = None


class UserBase(BaseModel):
    """Базовая схема пользователя."""
    username: str
    email: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Схема для создания пользователя."""
    password: str


class User(UserBase):
    """Схема пользователя (для ответов API)."""
    id: int

    class Config:
        orm_mode = True


class UserInDB(User):
    """Схема пользователя в базе данных."""
    password: str


class UserLogin(BaseModel):
    """Модель для входа пользователя"""
    username: str
    password: str 