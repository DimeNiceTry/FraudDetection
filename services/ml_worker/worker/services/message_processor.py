"""
Модуль для обработки сообщений из очереди.
"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from worker.services.ml import validate_data, make_prediction
from worker.services.prediction_service import update_prediction_result
from worker.services.rabbitmq_service import publish_result

logger = logging.getLogger(__name__)

def process_message(ch, method, properties, body, worker_id, db):
    """
    Обрабатывает сообщение из очереди.
    
    Args:
        ch: Канал RabbitMQ
        method: Метод доставки сообщения
        properties: Свойства сообщения
        body: Тело сообщения
        worker_id: Идентификатор ML-воркера
        db: Сессия базы данных
    """
    try:
        # Разбираем сообщение
        data = json.loads(body)
        logger.info(f"Получено сообщение для анализа транзакции. ID: {data.get('prediction_id', 'unknown')}")
        
        # Валидируем данные
        if not validate_data(data):
            logger.error("Валидация данных не пройдена. Сообщение не содержит необходимых полей.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        # Извлекаем необходимые данные
        prediction_id = data["prediction_id"]
        user_id = data["user_id"]
        input_data = data["data"]
        
        # Добавляем время начала обработки
        processing_start = datetime.now()
        logger.info(f"Начало анализа транзакции для предсказания {prediction_id}")
        
        # Выполняем предсказание на транзакции
        prediction_result = make_prediction(input_data)
        
        # Добавляем информацию о времени обработки
        processing_time = (datetime.now() - processing_start).total_seconds()
        logger.info(f"Анализ транзакции для {prediction_id} выполнен за {processing_time:.2f} сек.")
        
        # Обновляем результат в базе данных
        update_prediction_result(db, prediction_id, prediction_result, worker_id)
        
        # Публикуем результат в очередь
        publish_result(prediction_id, prediction_result)
        
        logger.info(f"Предсказание {prediction_id} успешно обработано")
        
        # Подтверждаем обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        # Подтверждаем сообщение даже в случае ошибки
        # В реальном приложении можно использовать стратегию повторных попыток
        ch.basic_ack(delivery_tag=method.delivery_tag) 