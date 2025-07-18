"""
Обработчики команд предсказания эмоций по фотографии.
"""
import logging
import base64
import io
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from services import (
    create_prediction,
    get_prediction_status,
    get_user_predictions
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Определяем состояния для FSM
class PredictionStates(StatesGroup):
    """Состояния для машины состояний предсказания."""
    waiting_for_photo = State() # Ожидание загрузки фото


async def cmd_predict(message: types.Message):
    """
    Обрабатывает команду /predict.
    Запрашивает фотографию для анализа эмоций.
    """
    # Создаем клавиатуру с кнопкой отмены
    cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_keyboard.add(types.KeyboardButton('/cancel'))
    
    await message.reply(
        "Пожалуйста, отправьте фотографию лица человека для распознавания эмоций. "
        "Или нажмите на кнопку /cancel для отмены.\n\n"
        "Для наилучших результатов рекомендуется фотография с четким изображением лица.",
        reply_markup=cancel_keyboard
    )
    await PredictionStates.waiting_for_photo.set()


async def cancel_prediction(message: types.Message, state: FSMContext):
    """
    Отменяет текущее предсказание.
    """
    from .common_handlers import get_main_keyboard
    
    await state.finish()
    await message.reply(
        "Предсказание отменено. Вы можете начать новое предсказание, используя команду /predict.",
        reply_markup=get_main_keyboard()
    )


async def process_photo(message: types.Message, state: FSMContext):
    """
    Обрабатывает фото, отправленное пользователем для предсказания эмоций.
    """
    from .common_handlers import get_main_keyboard
    import asyncio
    from datetime import datetime, timedelta
    
    if not message.photo:
        await message.reply("Пожалуйста, отправьте фотографию. Или используйте /cancel для отмены.")
        return
    
    telegram_id = message.from_user.id
    
    # Получаем информацию о фото (выбираем наибольший размер)
    photo = message.photo[-1]
    
    # Отправляем сообщение о получении фото
    status_message = await message.reply("🔄 Получаю фотографию и подготавливаю анализ...")
    
    try:
        # Скачиваем файл
        await status_message.edit_text("📥 Загружаю фотографию...")
        photo_file = await photo.get_file()
        photo_bytes = await message.bot.download_file(photo_file.file_path)
        
        # Конвертируем в base64
        await status_message.edit_text("🔄 Обрабатываю изображение...")
        photo_base64 = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
        
        # Создаем предсказание
        await status_message.edit_text("🔄 Отправляю данные на сервер для анализа...")
        prediction_id = await create_prediction(telegram_id, photo_base64)
        
        # Сохраняем ID предсказания в состоянии
        await state.update_data(prediction_id=prediction_id)
        
        # Сбрасываем состояние
        await state.finish()
        
        # Показываем сообщение о том, что фотография успешно отправлена на анализ
        # Удаляем старое сообщение о статусе для очистки чата
        await status_message.delete()
        
        # Отправляем новое сообщение о начале анализа
        processing_message = await message.reply("⏳ Фотография получена, выполняется анализ эмоций...")
        
        # Автоматическая проверка результата через несколько секунд
        max_retries = 6  # Максимальное количество попыток
        for retry in range(max_retries):
            await asyncio.sleep(5)  # Ждем 5 секунд между попытками
            
            try:
                # Проверяем статус предсказания
                prediction = await get_prediction_status(prediction_id)
                
                if prediction["status"] == "completed":
                    # Если предсказание завершено, удаляем сообщение о процессе и отправляем результат
                    await processing_message.delete()
                    
                    # Получаем эмоцию из результата
                    emotion = None
                    confidence = None
                    
                    if prediction["result"] and "translated_emotion" in prediction["result"]:
                        emotion = prediction["result"]["translated_emotion"]
                    elif prediction["result"] and "dominant_emotion" in prediction["result"]:
                        emotion = prediction["result"]["dominant_emotion"]
                    
                    if prediction["result"] and "confidence" in prediction["result"]:
                        confidence = prediction["result"]["confidence"]
                    
                    # Формируем сообщение только с информацией об эмоции
                    if emotion:
                        result_message = f"😀 На фотографии определена эмоция: {emotion}"
                        if confidence:
                            # Проверяем, что значение в диапазоне от 0 до 1
                            if confidence > 1:
                                # Если значение уже в процентах, оставляем как есть
                                result_message += f"\n🎯 Уверенность: {confidence:.1f}%"
                            else:
                                # Если значение от 0 до 1, умножаем на 100 для получения процентов
                                result_message += f"\n🎯 Уверенность: {confidence * 100:.1f}%"
                    else:
                        # Если эмоция не определена
                        result_message = "⚠️ Не удалось определить эмоцию на фотографии."
                    
                    await message.reply(result_message, reply_markup=get_main_keyboard())
                    break
                    
                elif retry == max_retries - 1:
                    # Если достигли последней попытки и результат всё ещё не готов
                    await processing_message.delete()
                    
                    # Создаем клавиатуру с кнопкой обновления статуса
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.add(types.KeyboardButton(f"/status {prediction_id}"))
                    keyboard.add(types.KeyboardButton("/predict"), types.KeyboardButton("/history"))
                    keyboard.add(types.KeyboardButton("/balance"), types.KeyboardButton("/help"))
                    
                    await message.reply(
                        f"⏳ Обработка фотографии занимает больше времени, чем ожидалось.\n"
                        f"Используйте кнопку ниже, чтобы проверить результат позже.",
                        reply_markup=keyboard
                    )
                    break
            except Exception as check_error:
                logger.error(f"Ошибка при автоматической проверке результата: {check_error}")
                if retry == max_retries - 1:
                    # При ошибке в последней попытке
                    await processing_message.delete()
                    await message.reply(
                        "Произошла ошибка при получении результатов анализа. Пожалуйста, попробуйте снова.",
                        reply_markup=get_main_keyboard()
                    )
        
    except ValueError as e:
        if status_message:
            await status_message.delete()
        await message.reply(
            f"❌ Ошибка: {str(e)}\n\nВы можете попробовать снова с другой фотографией.", 
            reply_markup=get_main_keyboard()
        )
        await state.finish()
        
    except Exception as e:
        logger.error(f"Ошибка при создании предсказания: {e}")
        if status_message:
            await status_message.delete()
        await message.reply(
            "❌ Произошла ошибка при обработке фотографии. Пожалуйста, попробуйте позже.", 
            reply_markup=get_main_keyboard()
        )
        await state.finish()


async def cmd_prediction_status(message: types.Message):
    """
    Обрабатывает команду /status.
    Получает статус предсказания пользователя по ID предсказания.
    """
    user_id = message.from_user.id
    prediction_id = get_prediction_id_from_message(message)

    if not prediction_id:
        await message.reply(
            "❌ Не указан ID предсказания.\n"
            "Используйте команду в формате: /status <prediction_id>"
        )
        return

    # Отправляем сообщение о проверке статуса
    status_message = await message.reply("🔄 Проверяю результат анализа...")

    try:
        # Получаем информацию о предсказании
        prediction = await get_prediction_status(prediction_id)

        # Если предсказание не найдено
        if not prediction:
            await status_message.delete()
            await message.reply("❌ Предсказание не найдено.")
            return

        # Проверяем статус предсказания
        status = prediction.get("status", "pending")

        if status == "pending":
            # Предсказание все еще в обработке
            await status_message.delete()
            await message.reply("⏳ Анализ все еще выполняется. Пожалуйста, попробуйте позже.")
        elif status == "completed":
            # Предсказание завершено
            result = prediction.get("result", {})
            
            # Получаем информацию об эмоции
            emotion = None
            confidence = None
            
            if result and "translated_emotion" in result:
                emotion = result["translated_emotion"]
            elif result and "dominant_emotion" in result:
                emotion = result["dominant_emotion"]
            
            if result and "confidence" in result:
                confidence = result["confidence"]
            
            # Формируем ответ с результатом
            response_text = f"✅ Анализ завершен\n\n"
            
            if emotion:
                response_text += f"😊 Определена эмоция: {emotion}\n"
                
                if confidence is not None:
                    # Проверяем, что значение в диапазоне от 0 до 1
                    if confidence > 1:
                        # Если значение уже в процентах, оставляем как есть
                        response_text += f"🎯 Уверенность: {confidence:.1f}%\n"
                    else:
                        # Если значение от 0 до 1, умножаем на 100 для получения процентов
                        response_text += f"🎯 Уверенность: {confidence * 100:.1f}%\n"
            else:
                response_text += "⚠️ Не удалось определить эмоцию на фотографии."
            
            await status_message.delete()
            await message.reply(response_text)
        else:
            # Ошибка предсказания
            await status_message.delete()
            await message.reply("❌ Произошла ошибка при анализе изображения.")
    except Exception as e:
        logger.error(f"Ошибка при получении статуса предсказания: {e}")
        await status_message.delete()
        await message.reply(
            "❌ Произошла ошибка при получении статуса предсказания.\n"
            "Пожалуйста, попробуйте позже."
        )


async def cmd_prediction_history(message: types.Message):
    """
    Обрабатывает команду /history.
    Показывает историю предсказаний пользователя.
    """
    from .common_handlers import get_main_keyboard
    from datetime import datetime, timedelta
    
    telegram_id = message.from_user.id
    
    # Отправляем сообщение о начале получения истории
    status_message = await message.reply("🔄 Получаю историю ваших предсказаний...")
    
    try:
        # Получаем историю предсказаний пользователя, передавая Telegram ID
        predictions = await get_user_predictions(telegram_id)
        
        if not predictions:
            await status_message.edit_text("📭 У вас пока нет предсказаний эмоций.")
            await message.reply(
                "Используйте команду /predict, чтобы создать новое предсказание.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Формируем сообщение с историей
        message_text = "📋 Ваши последние анализы эмоций:\n\n"
        
        for i, prediction in enumerate(predictions, 1):
            # Определяем статус и эмодзи
            if prediction["status"] == "pending":
                status_text = "⏳ В обработке"
                status_emoji = "⏳"
            elif prediction["status"] == "completed":
                status_text = "✅ Завершено"
                status_emoji = "✅"
            elif prediction["status"] == "failed":
                status_text = "❌ Ошибка"
                status_emoji = "❌"
            else:
                status_text = f"Статус: {prediction['status']}"
                status_emoji = "ℹ️"
            
            # Преобразуем время в московское (UTC+3)
            moscow_time = None
            if prediction["created_at"]:
                if isinstance(prediction["created_at"], str):
                    utc_time = datetime.fromisoformat(prediction["created_at"].replace('Z', '+00:00'))
                else:
                    utc_time = prediction["created_at"]
                moscow_time = utc_time + timedelta(hours=3)
                moscow_time_str = moscow_time.strftime('%d.%m.%Y %H:%M (МСК)')
            
            # Добавляем информацию о предсказании
            message_text += f"{i}. {status_emoji} Предсказание от {moscow_time_str}\n"
            message_text += f"   Статус: {status_text}\n"
            
            # Если предсказание завершено, добавляем результат
            if prediction["status"] == "completed" and prediction["result"] and "prediction" in prediction["result"]:
                result_preview = prediction["result"]["prediction"]
                if len(result_preview) > 50:
                    result_preview = result_preview[:50] + "..."
                message_text += f"   Результат: {result_preview}\n"
                
                # Если есть информация об эмоции, добавляем ее
                if "translated_emotion" in prediction["result"]:
                    message_text += f"   Эмоция: {prediction['result']['translated_emotion']}\n"
            
            message_text += "\n"
        
        # Обновляем сообщение с историей
        await status_message.edit_text(message_text)
        
        # Добавляем кнопку для нового предсказания
        await message.reply(
            "Хотите сделать новое предсказание? Используйте команду /predict.",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории предсказаний: {e}")
        await status_message.edit_text("❌ Произошла ошибка при получении истории предсказаний.")
        await message.reply(
            "Пожалуйста, попробуйте позже или создайте новое предсказание с помощью команды /predict.",
            reply_markup=get_main_keyboard()
        )

# Обработчик колбэк-кнопок истории предсказаний
async def process_prediction_callback(callback_query: types.CallbackQuery):
    """
    Обрабатывает нажатие на кнопку с информацией о предсказании.
    Отображает подробную информацию о выбранном предсказании.
    """
    user_id = callback_query.from_user.id
    callback_data = callback_query.data
    
    # Извлекаем ID предсказания из данных колбэка
    prediction_id = callback_data.split(':')[1] if ':' in callback_data else None
    
    if callback_data == "refresh_history":
        # Обрабатываем кнопку обновления истории
        message = callback_query.message
        await callback_query.answer("Обновляю историю...")
        
        # Удаляем текущее сообщение с историей
        await message.delete()
        
        # Создаем новое сообщение от имени пользователя
        fake_message = types.Message(
            chat=message.chat,
            from_user=callback_query.from_user,
            date=datetime.now(),
            text="/history",
            message_id=0
        )
        
        # Вызываем обработчик команды /history
        from .balance_handlers import cmd_prediction_history
        await cmd_prediction_history(fake_message)
        return
    
    if not prediction_id:
        await callback_query.answer("Некорректный ID предсказания")
        return
    
    # Отвечаем на колбэк, чтобы убрать часы загрузки
    await callback_query.answer("Получаю информацию о предсказании...")
    
    try:
        # Получаем информацию о предсказании
        prediction = await get_prediction_status(prediction_id)
        
        # Если предсказание не найдено
        if not prediction:
            await callback_query.message.reply("❌ Предсказание не найдено.")
            return
        
        # Преобразуем время создания в московское (UTC+3)
        created_at_moscow = None
        if prediction.get("created_at"):
            if isinstance(prediction["created_at"], str):
                created_utc = datetime.fromisoformat(prediction["created_at"].replace('Z', '+00:00'))
            else:
                created_utc = prediction["created_at"]
            created_at_moscow = created_utc + timedelta(hours=3)
            created_at_str = created_at_moscow.strftime('%d.%m.%Y %H:%M ')
        else:
            created_at_str = "Неизвестно"
        
        # Проверяем статус предсказания
        status = prediction.get("status", "pending")
        
        # Формируем сообщение с подробной информацией
        detail_text = f"📝 Подробная информация о предсказании\n\n"
        detail_text += f"🆔 ID: {prediction_id}\n"
        detail_text += f"🕒 Создано: {created_at_str}\n"
        detail_text += f"📊 Статус: "
        
        if status == "pending":
            detail_text += "⏳ В обработке\n"
            detail_text += "\nАнализ все еще выполняется. Пожалуйста, попробуйте позже."
        elif status == "completed":
            detail_text += "✅ Завершено\n\n"
            
            # Получаем информацию о результате предсказания
            result = prediction.get("result", {})
            
            # Добавляем информацию об эмоции
            emotion = None
            if "translated_emotion" in result:
                emotion = result["translated_emotion"]
            elif "dominant_emotion" in result:
                emotion = result["dominant_emotion"]
            
            if emotion:
                detail_text += f"😊 Определена эмоция: {emotion}\n"
            
            # Добавляем информацию о уверенности
            confidence = None
            if "confidence" in result:
                confidence = result["confidence"]
                if confidence is not None:
                    # Проверяем, что значение в диапазоне от 0 до 1
                    if confidence > 1:
                        # Если значение уже в процентах, оставляем как есть
                        detail_text += f"🎯 Уверенность: {confidence:.1f}%\n\n"
                    else:
                        # Если значение от 0 до 1, умножаем на 100 для получения процентов
                        detail_text += f"🎯 Уверенность: {confidence * 100:.1f}%\n\n"
            
            # Добавляем дополнительную информацию, если доступна
            if "emotion_scores" in result:
                detail_text += "📊 Распределение эмоций:\n"
                for emotion_name, score in sorted(result["emotion_scores"].items(), key=lambda x: x[1], reverse=True):
                    # Проверяем формат оценки
                    if score > 1:
                        # Если значение уже в процентах
                        detail_text += f"   - {emotion_name}: {score:.1f}%\n"
                    else:
                        # Если значение от 0 до 1
                        detail_text += f"   - {emotion_name}: {score * 100:.1f}%\n"
        else:
            detail_text += "❌ Ошибка\n"
            detail_text += "\nПроизошла ошибка при анализе изображения."
        
        # Создаем клавиатуру для возврата к истории
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="« Вернуться к истории", 
            callback_data="refresh_history"
        ))
        
        # Отправляем сообщение с подробной информацией
        await callback_query.message.reply(
            detail_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о предсказании: {e}")
        await callback_query.message.reply(
            "❌ Произошла ошибка при получении информации о предсказании.\n"
            "Пожалуйста, попробуйте позже."
        ) 