"""
Совместимость импортов для модуля аутентификации.
Этот файл создан для совместимости с существующими импортами.
"""

# Импортируем get_current_user из модуля security
from app.core.security import get_current_user

# Экспортируем get_current_user для совместимости
__all__ = ['get_current_user'] 