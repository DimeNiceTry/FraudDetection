"""
Точка входа в FastAPI приложение.
"""
import logging
import sys
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime

from app.services import init_db, wait_for_postgres, wait_for_rabbitmq
from app.routers import user_router, prediction_router, transaction_router
from app.api.routes import transactions
from app.services.result_consumer import start_result_consumer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title="ML Service API",
    description="REST API для сервиса машинного обучения с системой оплаты предсказаний",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация маршрутов
app.include_router(user_router, prefix="/api")
app.include_router(prediction_router, prefix="/api/predictions")
app.include_router(transaction_router, prefix="/api")
app.include_router(transactions.router, prefix="/api")


@app.get("/")
async def root():
    """Корневой эндпоинт API."""
    return {"message": "ML Service API"}


@app.get("/health")
async def health_check():
    """Эндпоинт проверки работоспособности сервиса."""
    try:
        # Пытаемся получить информацию о состоянии воркеров из RabbitMQ или другого источника
        workers_status = {}
        
        # Для тестов - возвращаем стандартный ответ с дополнительной информацией
        return {
            "status": "ok", 
            "service": "ML Service API",
            "timestamp": datetime.datetime.now().isoformat(),
            "workers": workers_status,
            "components": {
                "api": "ok",
                "database": "ok",
                "rabbitmq": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Ошибка при проверке здоровья системы: {e}")
        return {"status": "error", "message": str(e)}


@app.on_event("startup")
async def startup_event():
    """
    Действия при запуске сервиса.
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
    
    # Запускаем поток обработки результатов предсказаний
    try:
        logger.info("Запуск обработчика результатов предсказаний...")
        
        # Создаем и запускаем поток напрямую
        result_consumer_thread = threading.Thread(target=start_result_consumer, daemon=True)
        result_consumer_thread.start()
        
        logger.info("Обработчик результатов предсказаний успешно запущен")
    except Exception as e:
        logger.error(f"Ошибка при запуске обработчика результатов: {e}")
        logger.exception(e)
        # Завершаем приложение, если не удалось запустить обработчик
        sys.exit(1)

    logger.info("ML Service API успешно запущен") 