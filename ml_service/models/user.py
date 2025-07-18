"""
ORM модель пользователей.
"""
import bcrypt
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ml_service.models.base import Base

class User(Base):
    """Модель пользователя в системе."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    def verify_password(self, password: str) -> bool:
        """
        Проверить пароль пользователя с использованием bcrypt.
        
        Args:
            password: Пароль для проверки
            
        Returns:
            True если пароль верный, иначе False
        """
        try:
            password_bytes = password.encode('utf-8')
            hashed_bytes = self.password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            print(f"Ошибка при проверке пароля: {e}")
            return False
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>" 