"""
Базовый класс для ролей пользователей.
"""
from abc import ABC, abstractmethod
from typing import List, Set


class UserRole(ABC):
    """Абстрактный базовый класс для ролей пользователей."""
    
    @property
    @abstractmethod
    def permissions(self) -> Set[str]:
        """
        Получить список разрешений для данной роли.
        
        Returns:
            Множество строк с названиями разрешений
        """
        pass
    
    def has_permission(self, permission: str) -> bool:
        """
        Проверить наличие разрешения у роли.
        
        Args:
            permission: Название разрешения
            
        Returns:
            True если разрешение есть в списке разрешений роли, иначе False
        """
        return permission in self.permissions 