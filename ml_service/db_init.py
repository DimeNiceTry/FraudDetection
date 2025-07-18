"""
Скрипт для инициализации базы данных.
"""
import logging
from ml_service.db_config import init_db, SessionLocal
from ml_service.models import User, Balance

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_user():
    """
    Создает тестового пользователя, если его нет.
    """
    db = SessionLocal()
    try:
        # Проверяем, существует ли тестовый пользователь
        test_user = db.query(User).filter(User.username == "test").first()
        
        if not test_user:
            # Создаем тестового пользователя
            test_user = User(
                username="test",
                email="test@example.com",
                password="test",  # В реальном приложении хешировать пароль
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            # Создаем баланс для тестового пользователя
            balance = Balance(
                user_id=test_user.id,
                amount=100.0
            )
            db.add(balance)
            db.commit()
            
            logger.info("Тестовый пользователь создан")
        else:
            logger.info("Тестовый пользователь уже существует")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании тестового пользователя: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Инициализация базы данных...")
    init_db()
    create_test_user()
    logger.info("Инициализация базы данных завершена") 