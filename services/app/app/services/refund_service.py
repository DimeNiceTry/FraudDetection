"""
Сервис для обработки возврата кредитов.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.transactions import add_to_balance
from ml_service.models.prediction import Prediction

# Настройка логирования
logger = logging.getLogger(__name__)

def should_refund_credits(result: Dict[str, Any]) -> bool:
    """
    Проверяет, нужно ли возвращать кредиты по новым критериям.

    Критерии возврата:
    1. Статус предсказания равен failed или error
    2. В результате присутствует поле error
    3. Количество обнаруженных лиц равно 0
    4. Отсутствует информация об эмоциях при завершённом статусе
    5. Проверка текстовых сообщений о ненайденных лицах

    Args:
        result: Результат предсказания

    Returns:
        bool: True, если нужно вернуть кредиты, иначе False
    """
    # Критерий 1: Статус предсказания равен failed или error
    if result.get("status") in ["failed", "error"]:
        logger.info("Возврат кредитов: статус предсказания failed или error")
        return True

    # Критерий 2: В результате присутствует поле error
    if "error" in result:
        logger.info(f"Возврат кредитов: результат содержит ошибку: {result.get('error')}")
        return True

    # Критерий 3: Количество обнаруженных лиц равно 0
    if result.get("faces_count", 0) == 0:
        logger.info("Возврат кредитов: количество обнаруженных лиц равно 0")
        return True

    # Критерий 4: Отсутствует информация об эмоциях при завершённом статусе
    if result.get("status") == "completed" and not result.get("emotions") and not result.get("dominant_emotion"):
        logger.info("Возврат кредитов: отсутствует информация об эмоциях при завершённом статусе")
        return True
    
    # Критерий 5: Проверка текстовых сообщений о ненайденных лицах
    prediction_text = str(result.get("prediction", "")).lower()
    face_not_found_phrases = ["лица не обнаружены", "лицо не обнаружено", "no face detected", "face not found", "no faces found"]
    
    if any(phrase in prediction_text for phrase in face_not_found_phrases):
        logger.info(f"Возврат кредитов: в результате содержится информация о ненайденных лицах: '{prediction_text}'")
        return True

    return False

def process_refund(db: Session, prediction: Prediction, result: Dict[str, Any]) -> Optional[str]:
    """
    Обрабатывает возврат кредитов для предсказания.

    Args:
        db: Сессия базы данных
        prediction: Объект предсказания
        result: Результат предсказания

    Returns:
        Optional[str]: ID транзакции возврата или None, если возврат не был выполнен
    """
    # Проверяем, нужно ли возвращать кредиты
    if not should_refund_credits(result):
        logger.info(f"Возврат кредитов не требуется для предсказания {prediction.id}")
        return None

    # Извлекаем причину возврата
    refund_reason = "Возврат кредитов: "
    if result.get("status") in ["failed", "error"]:
        refund_reason += "некорректный статус предсказания"
    elif "error" in result:
        refund_reason += f"ошибка: {result.get('error')}"
    elif result.get("faces_count", 0) == 0:
        refund_reason += "лица не обнаружены"
    elif result.get("status") == "completed" and not result.get("emotions") and not result.get("dominant_emotion"):
        refund_reason += "отсутствует информация об эмоциях"
    else:
        # Проверяем текстовые сообщения о ненайденных лицах
        prediction_text = str(result.get("prediction", "")).lower()
        face_not_found_phrases = ["лица не обнаружены", "лицо не обнаружено", "no face detected", "face not found", "no faces found"]
        
        if any(phrase in prediction_text for phrase in face_not_found_phrases):
            refund_reason += "лица не найдены в результате анализа"
        else:
            refund_reason += "невыполненное предсказание"

    logger.info(f"Выполняем возврат кредитов для предсказания {prediction.id}. Причина: {refund_reason}")

    try:
        # Выполняем возврат кредитов
        prev_balance, new_balance, transaction_id = add_to_balance(
            db=db,
            user_id=prediction.user_id,
            amount=prediction.cost,
            description=refund_reason,
            related_entity_id=prediction.id
        )
        
        logger.info(f"Успешно выполнен возврат {prediction.cost} кредитов для пользователя {prediction.user_id}. "
                   f"Баланс до: {prev_balance}, после: {new_balance}, ID транзакции: {transaction_id}")
        
        return transaction_id
    except Exception as e:
        logger.error(f"Ошибка при возврате кредитов для предсказания {prediction.id}: {e}")
        logger.exception("Подробная информация об ошибке:")
        return None 