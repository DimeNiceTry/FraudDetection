"""
Сервис для обработки результатов предсказаний из очереди RabbitMQ.
"""
import logging
import json
import threading
import time
import pika
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.rabbitmq_service import get_rabbitmq_connection, ML_RESULT_QUEUE
from app.services.predictions import update_prediction_result, get_prediction_by_id
from app.services.transactions import add_to_balance
from ml_service.db_config import SessionLocal
from ml_service.models.balance import Balance
from ml_service.models.transaction import Transaction, TransactionType, TransactionStatus

# Настройка логирования
logger = logging.getLogger(__name__)

def process_result_message(ch, method, properties, body):
    """
    Обрабатывает сообщение о результате предсказания из очереди.
    
    Args:
        ch: Канал RabbitMQ
        method: Метод доставки сообщения
        properties: Свойства сообщения
        body: Тело сообщения
    """
    logger.info(f"===== НАЧАЛО ОБРАБОТКИ СООБЩЕНИЯ =====")
    logger.info(f"Получено сообщение из очереди: {body[:200]}...")
    
    db = SessionLocal()
    try:
        # Разбираем сообщение
        data = json.loads(body)
        prediction_id = data.get("prediction_id")
        
        logger.info(f"Разобрано сообщение, prediction_id: {prediction_id}")
        
        if not prediction_id:
            logger.error("Отсутствует prediction_id в сообщении")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        result = data.get("result", {})
        
        # Получаем информацию о предсказании из базы данных
        prediction = get_prediction_by_id(db, prediction_id)
        if not prediction:
            logger.error(f"Предсказание с ID {prediction_id} не найдено в базе данных")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        original_status = prediction.status
        logger.info(f"Обработка результата для предсказания {prediction_id}, текущий статус: {original_status}")
        logger.info(f"Содержимое результата: {json.dumps(result, indent=2)[:500]}...")
        
        # Обновляем результат предсказания
        prediction = update_prediction_result(db, prediction_id, result, result.get("worker_id", "unknown"))
        if not prediction:
            logger.error(f"Не удалось обновить предсказание {prediction_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        logger.info(f"Обновлено предсказание {prediction_id}, текущий статус: {prediction.status}")
        
        # НОВАЯ ЛОГИКА: По умолчанию всегда возвращаем кредиты при ошибке
        # Единственное исключение - успешное завершение с результатом
        need_refund = True  # По умолчанию возвращаем кредиты
        
        # Проверяем, является ли результат успешным
        is_successful = False
        
        # Проверим все нужные условия для успешного результата
        if prediction.status == 'completed':
            # Соберем список возможных проблем
            issues = []
            
            # Проверка #1: Должна присутствовать доминирующая эмоция
            if result.get("dominant_emotion") is None:
                issues.append("Отсутствует dominant_emotion")
            
            # Проверка #2: Уверенность должна быть больше 0
            if result.get("confidence", 0) <= 0:
                issues.append(f"Низкая уверенность: {result.get('confidence', 0)}")
            
            # Проверка #3: Не должно быть ошибок
            if "error" in result:
                issues.append(f"Присутствует ошибка: {result.get('error')}")
            
            # Проверка #4: Количество лиц должно быть больше 0
            if result.get("faces_count", 0) <= 0:
                issues.append(f"Не обнаружено лиц: faces_count={result.get('faces_count', 0)}")
            
            # Проверка #5: Проверка текстового сообщения о ненайденных лицах
            prediction_text = str(result.get("prediction", "")).lower()
            face_not_found_phrases = ["лица не обнаружены", "лицо не обнаружено", "no face detected", "face not found", "no faces found"]
            
            if any(phrase in prediction_text for phrase in face_not_found_phrases):
                issues.append(f"В результате содержится информация о том, что лицо не найдено: '{prediction_text}'")
            
            # Если нет проблем, значит предсказание успешно
            if not issues:
                is_successful = True
                logger.info(f"Предсказание {prediction_id} успешно: обнаружено {result.get('faces_count', 1)} лиц, эмоция: {result.get('dominant_emotion')}")
            else:
                logger.info(f"Предсказание {prediction_id} неуспешно по следующим причинам:")
                for issue in issues:
                    logger.info(f"- {issue}")
        else:
            logger.info(f"Предсказание {prediction_id} имеет статус '{prediction.status}', отличный от 'completed'")
        
        # Если предсказание успешно, НЕ возвращаем кредиты
        if is_successful:
            need_refund = False
            logger.info(f"Предсказание {prediction_id} успешно выполнено, возврат кредитов НЕ требуется")
        else:
            logger.info(f"Предсказание {prediction_id} требует возврата кредитов")
        
        logger.info(f"Итоговое решение о возврате кредитов: {need_refund}")
        
        if need_refund:
            logger.info(f"=== НАЧИНАЕМ ПРОЦЕДУРУ ВОЗВРАТА КРЕДИТОВ ===")
            logger.info(f"Возвращаем кредиты за предсказание {prediction_id}")
            refund_success = False
            max_attempts = 3
            attempts = 0
            
            # Инициализируем user_id
            user_id = None
            if isinstance(prediction.user_id, str):
                try:
                    user_id = int(prediction.user_id)
                except ValueError:
                    logger.error(f"Невозможно преобразовать user_id '{prediction.user_id}' в целое число")
            else:
                user_id = prediction.user_id
            
            logger.info(f"user_id: {user_id}, тип: {type(user_id)}")
            
            # Проверяем, что cost не None и больше 0
            if not prediction.cost or prediction.cost <= 0:
                logger.error(f"Некорректная стоимость предсказания: {prediction.cost}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            logger.info(f"Подготовка к возврату {prediction.cost} кредитов пользователю {user_id}")
            
            # Значения Enum для логирования
            refund_type_value = TransactionType.REFUND.value if hasattr(TransactionType.REFUND, 'value') else str(TransactionType.REFUND)
            completed_status_value = TransactionStatus.COMPLETED.value if hasattr(TransactionStatus.COMPLETED, 'value') else str(TransactionStatus.COMPLETED)
            
            logger.info(f"Значения Enum: refund_type={refund_type_value}, completed_status={completed_status_value}")

            # Проверяем, была ли уже возвращена сумма за это предсказание
            existing_refund = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.type == refund_type_value,
                Transaction.related_entity_id == str(prediction_id)
            ).first()
            
            if existing_refund:
                logger.info(f"Обнаружен существующий возврат для предсказания {prediction_id}, пропускаем повторный возврат")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Используем единую функцию для возврата средств
            try:
                # Вызываем функцию add_to_balance для добавления средств на баланс пользователя
                prev_balance, new_balance, tx_id = add_to_balance(
                    db=db, 
                    user_id=user_id, 
                    amount=prediction.cost, 
                    description=f"Возврат средств за предсказание {prediction_id} (неуспешное предсказание)", 
                    related_entity_id=str(prediction_id)
                )
                
                logger.info(f"✅ Кредиты успешно возвращены. Баланс изменен с {prev_balance} на {new_balance}. ID транзакции: {tx_id}")
                refund_success = True
                
            except Exception as e:
                logger.error(f"❌ Ошибка при возврате кредитов: {e}")
                logger.exception("Подробная информация об ошибке:")
                
                # Попытка альтернативного способа возврата средств
                try:
                    logger.info("Пробуем альтернативный способ возврата средств...")
                    
                    # Создаем новую сессию
                    db.close()
                    db = SessionLocal()
                    
                    # Получаем баланс пользователя
                    balance = db.query(Balance).filter(Balance.user_id == user_id).first()
                    if not balance:
                        balance = Balance(user_id=user_id, amount=0)
                        db.add(balance)
                        db.flush()
                    
                    prev_balance = balance.amount
                    
                    # Создаем транзакцию напрямую
                    transaction = Transaction(
                        user_id=user_id,
                        amount=int(prediction.cost * 100),  # Храним в копейках/центах
                        type=refund_type_value,
                        status=completed_status_value,
                        description=f"Возврат средств за предсказание {prediction_id} (аварийный возврат)",
                        related_entity_id=str(prediction_id)
                    )
                    
                    db.add(transaction)
                    
                    # Обновляем баланс
                    balance.amount += prediction.cost
                    
                    db.commit()
                    
                    # Проверяем результат
                    updated_balance = db.query(Balance).filter(Balance.user_id == user_id).first()
                    new_balance = updated_balance.amount if updated_balance else 0
                    
                    logger.info(f"✅ Кредиты возвращены альтернативным способом. Баланс изменен с {prev_balance} на {new_balance}")
                    refund_success = True
                    
                except Exception as alt_error:
                    logger.error(f"❌ Ошибка при альтернативном возврате кредитов: {alt_error}")
                    logger.exception("Подробная информация об ошибке альтернативного возврата:")
            
            if not refund_success:
                logger.error(f"❌ Не удалось вернуть кредиты за предсказание {prediction_id} после всех попыток")
            
        else:
            logger.info(f"Возврат кредитов не требуется для предсказания {prediction_id}")
        
        logger.info(f"Результат предсказания {prediction_id} успешно обработан")
        logger.info(f"===== ЗАВЕРШЕНИЕ ОБРАБОТКИ СООБЩЕНИЯ =====")
        
        # Подтверждаем обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке результата: {e}")
        logger.exception("Подробная информация об ошибке:")
        
        # Подтверждаем обработку сообщения, даже если произошла ошибка
        # Это предотвратит повторную доставку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
    finally:
        db.close()


def start_result_consumer():
    """
    Запускает потребителя результатов предсказаний.
    """
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
        
        # Устанавливаем количество сообщений, которые могут быть обработаны одновременно
        channel.basic_qos(prefetch_count=1)
        
        # Начинаем потреблять сообщения
        channel.basic_consume(queue=ML_RESULT_QUEUE, on_message_callback=process_result_message)
        
        logger.info(f"Начинаем потребление результатов из очереди {ML_RESULT_QUEUE}")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Ошибка при запуске потребителя результатов: {e}")
        logger.exception("Подробная информация об ошибке:")


def run_result_consumer_thread():
    """
    Запускает потребителя результатов в отдельном потоке.
    """
    thread = threading.Thread(target=start_result_consumer)
    thread.daemon = True
    thread.start()
    return thread 