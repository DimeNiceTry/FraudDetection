"""
Сервисы для Telegram бота.
"""

from .db_service import (
    get_db_connection,
    wait_for_db,
    register_user,
    get_user_balance,
    add_user_balance,
    get_db_user_id
)

from .rabbitmq_service import (
    get_rabbitmq_connection,
    wait_for_rabbitmq, 
    publish_message,
    ML_TASK_QUEUE,
    ML_RESULT_QUEUE
)

from .prediction_service import (
    create_prediction,
    get_prediction_status,
    get_user_predictions
)

__all__ = [
    # Сервис базы данных
    "get_db_connection",
    "wait_for_db",
    "register_user",
    "get_user_balance",
    "add_user_balance",
    "get_db_user_id",
    
    # Сервис RabbitMQ
    "get_rabbitmq_connection",
    "wait_for_rabbitmq",
    "publish_message",
    "ML_TASK_QUEUE",
    "ML_RESULT_QUEUE",
    
    # Сервис предсказаний
    "create_prediction",
    "get_prediction_status",
    "get_user_predictions"
] 