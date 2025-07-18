"""
Определения ролей пользователей системы.
"""
from typing import Set
from ml_service.models.base.user_role import UserRole


class RegularUserRole(UserRole):
    """Обычный пользователь системы."""
    
    @property
    def permissions(self) -> Set[str]:
        """
        Получить список разрешений для обычного пользователя.
        
        Returns:
            Множество строк с названиями разрешений
        """
        return {
            'prediction:create',
            'prediction:read_own',
            'balance:read_own',
            'balance:topup',
            'transaction:read_own',
            'user:read_own',
            'user:update_own'
        }


class AdminRole(UserRole):
    """Администратор системы."""
    
    @property
    def permissions(self) -> Set[str]:
        """
        Получить список разрешений для администратора.
        
        Returns:
            Множество строк с названиями разрешений
        """
        return {
            'prediction:create',
            'prediction:read_own',
            'prediction:read_all',
            'balance:read_own',
            'balance:read_all',
            'balance:topup',
            'balance:modify',
            'transaction:read_own',
            'transaction:read_all',
            'user:read_own',
            'user:read_all',
            'user:update_own',
            'user:update_all',
            'user:create',
            'user:delete',
            'admin:access',
            'system:manage'
        } 