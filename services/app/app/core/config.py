"""
Конфигурация приложения.
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Настройки приложения."""
    # Настройки приложения
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    
    # Настройки базы данных
    DB_HOST: str = os.getenv("DB_HOST", "database")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "ml_service")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "postgres")
    
    # Настройки RabbitMQ
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "guest")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    ML_TASK_QUEUE: str = "ml_tasks"
    ML_RESULT_QUEUE: str = "ml_results"
    
    # Настройки JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret_key_for_jwt")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки ML
    PREDICTION_COST: float = float(os.getenv("PREDICTION_COST", "1.0"))

    class Config:
        env_file = ".env"

# Создаем глобальный экземпляр настроек
settings = Settings() 