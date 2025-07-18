"""
Модель пользователя системы.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import bcrypt
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ml_service.models.base.entity import Entity
from ml_service.models.base.user_role import UserRole
from ml_service.models.users.roles import RegularUserRole


class User(Entity):
    """Модель пользователя системы."""
    
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role_name = Column(String, default="RegularUserRole", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Отношение к балансу (один-к-одному)
    balance = relationship("Balance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    # Отношение к транзакциям (один-ко-многим)
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

    def __init__(
        self, 
        username: str, 
        email: str, 
        password_hash: str, 
        role: UserRole = None, 
        id: str = None
    ):
        super().__init__(id)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role_name = role.__class__.__name__ if role else RegularUserRole().__class__.__name__
        self.is_active = True
        self.last_login = None
        self._role = role if role else RegularUserRole()

    @property
    def role(self) -> UserRole:
        return self._role

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Хеширует пароль с использованием bcrypt.
        
        Args:
            password: Пароль для хеширования
            
        Returns:
            Хеш пароля в виде строки
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """
        Проверить пароль пользователя с использованием bcrypt.
        
        Args:
            password: Пароль для проверки
            
        Returns:
            True если пароль верный, иначе False
        """
        password_bytes = password.encode('utf-8')
        hashed_bytes = self.password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def has_permission(self, permission: str) -> bool:
        """
        Проверить наличие разрешения у пользователя.
        
        Args:
            permission: Название разрешения
            
        Returns:
            True если разрешение есть у роли пользователя, иначе False
        """
        return self._role.has_permission(permission)

    def set_role(self, role: UserRole) -> None:
        """
        Установить роль пользователя.
        
        Args:
            role: Новая роль пользователя
        """
        self._role = role
        self.role_name = role.__class__.__name__
        self.update()

    def record_login(self) -> None:
        """Записать время последнего входа в систему."""
        self.last_login = datetime.now()
        self.update()

    def activate(self) -> None:
        """Активировать учетную запись пользователя."""
        self.is_active = True
        self.update()

    def deactivate(self) -> None:
        """Деактивировать учетную запись пользователя."""
        self.is_active = False
        self.update()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать пользователя в словарь для сериализации.
        
        Returns:
            Словарь с данными пользователя
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role_name,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 