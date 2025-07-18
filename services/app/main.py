#!/usr/bin/env python3
"""
Точка входа для FastAPI приложения.
"""
import uvicorn
import logging
import sys

from app import create_app
from app.services import init_db, wait_for_rabbitmq

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем экземпляр приложения
app = create_app()

@app.on_event("startup")
async def startup_event():
    """
    Действия при запуске сервиса.
    - Инициализация базы данных
    - Проверка подключения к RabbitMQ
    """
    logger.info("Запуск ML Service API")
    
    # Инициализация базы данных
    if not init_db():
        logger.error("Ошибка инициализации базы данных")
        sys.exit(1)
    
    # Проверка подключения к RabbitMQ
    if not wait_for_rabbitmq():
        logger.error("Ошибка подключения к RabbitMQ")
        sys.exit(1)
    
    logger.info("ML Service API успешно запущен")

if __name__ == "__main__":
    logger.info("Запуск приложения на http://0.0.0.0:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False) 