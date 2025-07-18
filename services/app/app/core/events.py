"""
События жизненного цикла приложения.
"""
import logging
from app.db.init_db import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def startup_event():
    """Событие при запуске приложения."""
    logger.info("Приложение запускается...")
    
    # Инициализация базы данных
    if not init_db():
        logger.error("Не удалось инициализировать базу данных!")
    
    logger.info("Приложение готово к работе.") 