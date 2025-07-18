"""
Обработчики команд для работы с балансом.
"""
import logging
import re
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from services import get_user_balance, add_user_balance
from services.db_service import get_db_connection, get_db_user_id

# Настройка логирования
logger = logging.getLogger(__name__)

# Состояния для пополнения баланса
class BalanceStates(StatesGroup):
    waiting_for_amount = State()

async def cmd_balance(message: types.Message):
    """
    Обрабатывает команду /balance.
    Показывает текущий баланс пользователя.
    """
    from .common_handlers import get_main_keyboard
    
    telegram_id = message.from_user.id
    
    # Отправляем сообщение о начале получения баланса
    status_message = await message.reply("🔄 Получаю информацию о вашем балансе...")
    
    try:
        # Получаем внутренний ID пользователя из базы данных
        db_user_id = await get_db_user_id(telegram_id)
        
        if not db_user_id:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            await status_message.edit_text("❌ Ошибка: ваш аккаунт не найден.")
            await message.reply(
                "Пожалуйста, используйте /start для регистрации.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Получаем баланс пользователя используя внутренний ID
        balance = await get_user_balance(db_user_id)
        
        # Отправляем сообщение с балансом
        await status_message.edit_text(
            f"💰 Ваш текущий баланс: {balance:.2f} кредитов"
        )
        
        # Предлагаем пополнить баланс или сделать предсказание
        if balance < 1:
            # Если баланса не хватает на предсказание
            await message.reply(
                "❗ У вас недостаточно кредитов для предсказания.\n"
                "Каждое предсказание стоит 1 кредит.\n\n"
                "Используйте команду /topup для пополнения баланса.",
                reply_markup=get_main_keyboard()
            )
        else:
            # Если на балансе достаточно средств
            await message.reply(
                f"✅ У вас достаточно кредитов для предсказаний ({int(balance)} шт).\n"
                "Каждое предсказание стоит 1 кредит.\n\n"
                "Хотите сделать предсказание? Используйте команду /predict.\n"
                "Или пополните баланс с помощью команды /topup.",
                reply_markup=get_main_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        await status_message.edit_text("❌ Произошла ошибка при получении информации о балансе.")
        await message.reply(
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

async def cmd_topup(message: types.Message):
    """
    Обрабатывает команду /topup.
    Запускает процесс пополнения баланса.
    """
    # Создаем клавиатуру с кнопкой отмены
    cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_keyboard.add(types.KeyboardButton('/cancel'))
    
    await message.reply(
        "💰 Пополнение баланса\n\n"
        "Введите сумму пополнения (число от 1 до 100):\n\n"
        "Для отмены нажмите /cancel",
        reply_markup=cancel_keyboard
    )
    # Устанавливаем состояние ожидания суммы пополнения
    await BalanceStates.waiting_for_amount.set()

async def process_topup_amount(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод суммы пополнения.
    """
    from .common_handlers import get_main_keyboard
    
    telegram_id = message.from_user.id
    text = message.text.strip()
    
    # Отправляем сообщение о начале обработки пополнения
    status_message = await message.reply("🔄 Обрабатываю запрос на пополнение баланса...")
    
    # Проверяем, что введено число
    if not re.match(r'^\d+(\.\d+)?$', text):
        await status_message.edit_text("❌ Ошибка: введено некорректное число.")
        await message.reply(
            "Пожалуйста, введите корректное число от 1 до 100.",
            reply_markup=get_main_keyboard()
        )
        await state.finish()
        return
    
    amount = float(text)
    
    # Проверяем, что сумма в допустимых пределах
    if amount < 1 or amount > 100:
        await status_message.edit_text("❌ Ошибка: некорректная сумма пополнения.")
        await message.reply(
            "Сумма пополнения должна быть от 1 до 100 кредитов.",
            reply_markup=get_main_keyboard()
        )
        await state.finish()
        return
    
    try:
        # Получаем внутренний ID пользователя из базы данных
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info(f"Получение внутреннего ID пользователя для Telegram ID: {telegram_id}")
        cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{telegram_id}",))
        user_record = cursor.fetchone()
        
        if not user_record:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            await status_message.edit_text("❌ Ошибка: ваш аккаунт не найден.")
            await message.reply(
                "Пожалуйста, используйте /start для регистрации.",
                reply_markup=get_main_keyboard()
            )
            await state.finish()
            conn.close()
            return
        
        db_user_id = user_record[0]
        logger.info(f"Найден внутренний ID пользователя: {db_user_id} для Telegram ID: {telegram_id}")
        conn.close()
        
        # Обновляем статус
        await status_message.edit_text(f"🔄 Пополняю баланс на {amount:.2f} кредитов...")
        
        # Пополняем баланс используя внутренний ID
        new_balance = await add_user_balance(db_user_id, amount)
        
        # Сбрасываем состояние
        await state.finish()
        
        # Отправляем сообщение об успешном пополнении
        await status_message.edit_text(
            f"✅ Баланс успешно пополнен на {amount:.2f} кредитов!"
        )
        
        await message.reply(
            f"💰 Ваш новый баланс: {new_balance:.2f} кредитов.\n\n"
            "Теперь вы можете сделать предсказание с помощью команды /predict.",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса: {e}")
        await status_message.edit_text("❌ Произошла ошибка при пополнении баланса.")
        await message.reply(
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        await state.finish()

async def cancel_topup(message: types.Message, state: FSMContext):
    """
    Отменяет процесс пополнения баланса.
    """
    from .common_handlers import get_main_keyboard
    
    current_state = await state.get_state()
    if current_state == BalanceStates.waiting_for_amount.state:
        await state.finish()
        await message.reply(
            "❌ Пополнение баланса отменено.\n\n"
            "Вы можете выбрать другое действие.",
            reply_markup=get_main_keyboard()
        )
        return True
    return False

async def cmd_prediction_history(message: types.Message):
    """
    Обрабатывает команду /history.
    Отображает историю предсказаний пользователя.
    """
    from datetime import datetime, timedelta
    from .common_handlers import get_main_keyboard
    
    user_id = message.from_user.id
    
    # Отправляем сообщение о загрузке истории
    status_message = await message.reply("🔄 Загружаю историю предсказаний...")
    
    try:
        # Получаем историю предсказаний пользователя
        predictions = await get_user_predictions(user_id)
        
        # Удаляем сообщение о загрузке
        await status_message.delete()
        
        if not predictions:
            await message.reply(
                "📋 У вас пока нет истории предсказаний.\n"
                "Используйте команду /predict, чтобы сделать первое предсказание!",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Формируем сообщение с историей предсказаний
        history_text = "📋 История ваших последних предсказаний:\n\n"
        
        # Создаем клавиатуру с кнопками для просмотра подробной информации
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Ограничиваем количество предсказаний в истории
        max_predictions = 5
        recent_predictions = predictions[:max_predictions]
        
        for index, prediction in enumerate(recent_predictions, 1):
            # Преобразуем время создания в московское (UTC+3)
            created_at_moscow = None
            if prediction["created_at"]:
                if isinstance(prediction["created_at"], str):
                    created_utc = datetime.fromisoformat(prediction["created_at"].replace('Z', '+00:00'))
                else:
                    created_utc = prediction["created_at"]
                created_at_moscow = created_utc + timedelta(hours=3)
                created_at_str = created_at_moscow.strftime('%d.%m.%Y %H:%M (МСК)')
            else:
                created_at_str = "Неизвестно"
            
            # Получаем информацию об эмоции из результата
            emotion = "Неизвестно"
            if prediction["status"] == "completed" and prediction["result"]:
                if "translated_emotion" in prediction["result"]:
                    emotion = prediction["result"]["translated_emotion"]
                elif "dominant_emotion" in prediction["result"]:
                    emotion = prediction["result"]["dominant_emotion"]
            elif prediction["status"] == "pending":
                emotion = "⏳ В обработке"
            elif prediction["status"] == "failed":
                emotion = "❌ Ошибка анализа"
            
            # Добавляем информацию о предсказании
            history_text += f"{index}. {created_at_str}\n"
            history_text += f"   Эмоция: {emotion}\n\n"
            
            # Добавляем кнопку для просмотра подробной информации
            keyboard.add(types.InlineKeyboardButton(
                text=f"{index}. {emotion} ({created_at_str})",
                callback_data=f"prediction:{prediction['prediction_id']}"
            ))
        
        # Добавляем кнопку для обновления истории
        keyboard.add(types.InlineKeyboardButton(
            text="🔄 Обновить историю", 
            callback_data="refresh_history"
        ))
        
        # Отправляем историю с кнопками
        await message.reply(
            history_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории предсказаний: {e}")
        await status_message.delete()
        await message.reply(
            "❌ Произошла ошибка при получении истории предсказаний.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        ) 