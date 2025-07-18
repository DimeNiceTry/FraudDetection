"""
Менеджер для работы с пользователями.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ml_service.models.users.user import User
from ml_service.models.users.roles import AdminRole, RegularUserRole
from ml_service.models.base.user_role import UserRole
from ml_service.models.transactions.balance import Balance


class UserManager:
    """Менеджер для работы с пользователями."""
    
    def __init__(self, db_session: Session):
        """
        Инициализация менеджера пользователей.
        
        Args:
            db_session: Сессия базы данных
        """
        self.db = db_session
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole = None, is_active: bool = True) -> User:
        """
        Создать нового пользователя.
        
        Args:
            username: Имя пользователя
            email: Email пользователя
            password: Пароль пользователя
            role: Роль пользователя (по умолчанию RegularUserRole)
            is_active: Активен ли пользователь
            
        Returns:
            Созданный пользователь
        """
        # Проверяем, что пользователь с таким именем или email не существует
        existing_user = self.db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise ValueError(f"Пользователь с именем {username} или email {email} уже существует")
        
        # Хешируем пароль
        password_hash = User.hash_password(password)
        
        # Создаем пользователя
        user = User(
            username=username, 
            email=email, 
            password_hash=password_hash,
            role=role
        )
        
        if not is_active:
            user.deactivate()
        
        # Добавляем пользователя в базу
        self.db.add(user)
        
        # Создаем баланс для пользователя
        balance = Balance(user_id=user.id)
        self.db.add(balance)
        
        # Сохраняем изменения
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Получить пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Пользователь или None, если не найден
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получить пользователя по имени.
        
        Args:
            username: Имя пользователя
            
        Returns:
            Пользователь или None, если не найден
        """
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получить пользователя по email.
        
        Args:
            email: Email пользователя
            
        Returns:
            Пользователь или None, если не найден
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all_users(self) -> List[User]:
        """
        Получить всех пользователей.
        
        Returns:
            Список всех пользователей
        """
        return self.db.query(User).all()
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> Optional[User]:
        """
        Обновить данные пользователя.
        
        Args:
            user_id: ID пользователя
            data: Словарь с данными для обновления
            
        Returns:
            Обновленный пользователь или None, если не найден
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Обновляем поля пользователя
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'password' in data:
            user.password_hash = User.hash_password(data['password'])
        if 'is_active' in data:
            if data['is_active']:
                user.activate()
            else:
                user.deactivate()
        
        # Сохраняем изменения
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """
        Удалить пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если пользователь удален, иначе False
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Аутентифицировать пользователя.
        
        Args:
            username: Имя пользователя
            password: Пароль пользователя
            
        Returns:
            Пользователь если аутентификация успешна, иначе None
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if not user.verify_password(password):
            return None
        
        if not user.is_active:
            return None
        
        user.record_login()
        self.db.commit()
        
        return user 