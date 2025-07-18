"""
Инициализация FastAPI приложения.
"""
import logging
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Удаляем неправильные импорты
# from app.api.routes import router
# from app.middleware.auth import AuthMiddleware
from app.services.result_consumer import run_result_consumer_thread, start_result_consumer
from app.core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Создание и конфигурация экземпляра FastAPI."""
    app = FastAPI(
        title="ML Service API",
        description="REST API для сервиса машинного обучения с системой оплаты предсказаний",
        version="1.0.0"
    )
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Убираем добавление несуществующего middleware
    # app.add_middleware(AuthMiddleware)
    
    # Импортируем и регистрируем маршруты только из одного места
    from app.api.routes import auth, users, predictions, balance, healthcheck
    
    # Регистрируем маршруты с единым префиксом
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(predictions.router, prefix="/api")
    app.include_router(balance.router, prefix="/api")
    app.include_router(healthcheck.router)
    
    # Добавляем тестовый маршрут для проверки
    @app.get("/api/test")
    async def test_endpoint():
        return {"status": "ok", "message": "API endpoint is working!"}
    
    # Функция мониторинга потребителя результатов
    def monitor_result_consumer_thread():
        """
        Мониторит и перезапускает потребителя результатов, если он упал.
        """
        consumer_thread = None
        while True:
            # Если потока нет или он завершился
            if consumer_thread is None or not consumer_thread.is_alive():
                logger.warning("Поток обработки результатов неактивен. Запускаем новый...")
                consumer_thread = threading.Thread(target=start_result_consumer, daemon=True)
                consumer_thread.start()
                logger.info("Новый поток обработки результатов запущен")
            
            # Проверяем статус каждые 30 секунд
            time.sleep(30)
    
    # Регистрируем обработчик события запуска приложения
    @app.on_event("startup")
    async def startup():
        """
        Выполняется при запуске приложения.
        """
        logger.info("Запуск приложения")
        
        # Запускаем обработчик результатов в отдельном потоке
        run_result_consumer_thread()
        
        # Запускаем мониторинг потока обработки результатов
        monitoring_thread = threading.Thread(target=monitor_result_consumer_thread, daemon=True)
        monitoring_thread.start()
        logger.info("Запущен мониторинг потока обработки результатов")
    
    return app 