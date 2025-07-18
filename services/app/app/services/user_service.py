"""
Сервис для работы с пользователями.
"""
import logging
from app.services.db_service import get_db_connection
from app.models.user import User

# Настройка логирования
logger = logging.getLogger(__name__)

def create_user(username, email, password):
    """
    Создает нового пользователя.
    
    Args:
        username: Имя пользователя
        email: Email пользователя
        password: Пароль пользователя
        
    Returns:
        User: Созданный пользователь
        
    Raises:
        ValueError: Если пользователь с таким именем уже существует
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь с таким именем
        cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            raise ValueError(f"Пользователь с именем {username} уже существует")
        
        # Создаем нового пользователя
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
            (username, email, password)  # В реальном приложении пароль нужно хешировать
        )
        user_id = cursor.fetchone()[0]
        
        # Создаем баланс для пользователя
        cursor.execute(
            "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
            (user_id, 10.0)  # Начальный баланс 10 кредитов
        )
        
        conn.commit()
        
        # Возвращаем данные о созданном пользователе
        return User(id=user_id, username=username, email=email, is_active=True)
    
    except ValueError as e:
        if conn:
            conn.rollback()
        logger.warning(str(e))
        raise
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Ошибка при создании пользователя: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def get_user_by_username(username):
    """
    Получает пользователя по имени.
    
    Args:
        username: Имя пользователя
        
    Returns:
        User: Найденный пользователь или None
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, email, is_active FROM users WHERE username = %s",
            (username,)
        )
        user_row = cursor.fetchone()
        
        if not user_row:
            return None
        
        return User(
            id=user_row[0],
            username=user_row[1],
            email=user_row[2],
            is_active=user_row[3]
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """
    Получает пользователя по ID.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        User: Найденный пользователь или None
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, email, is_active FROM users WHERE id = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()
        
        if not user_row:
            return None
        
        return User(
            id=user_row[0],
            username=user_row[1],
            email=user_row[2],
            is_active=user_row[3]
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        raise
    
    finally:
        if conn:
            conn.close() 