"""
Общие обработчики команд Telegram бота.
"""
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from services.db_service import register_user

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем клавиатуру с кнопками команд
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('/predict'))
    keyboard.add(KeyboardButton('/balance'), KeyboardButton('/topup'))
    keyboard.add(KeyboardButton('/history'), KeyboardButton('/help'))
    return keyboard

async def send_welcome(message: types.Message):
    """
    Обрабатывает команды /start и /help.
    """
    logger.info(f"Получена команда '/start' или '/help' от пользователя {message.from_user.id} ({message.from_user.username})")
    
    try:
        # Регистрируем пользователя при первом использовании бота
        logger.info(f"Регистрируем пользователя {message.from_user.id}")
        user_id = await register_user(message.from_user.id, message.from_user.username or "user")
        logger.info(f"Пользователь {message.from_user.id} успешно зарегистрирован, ID в БД: {user_id}")
        
        # Создаем клавиатуру с кнопками команд
        keyboard = get_main_keyboard()
        
        await message.reply(
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я бот для демонстрации ML сервиса. С моей помощью ты можешь отправлять запросы "
            "на предсказание и получать результаты.\n\n"
            "Доступные команды:\n"
            "/predict - сделать предсказание\n"
            "/balance - проверить баланс\n"
            "/topup - пополнить баланс\n"
            "/history - история предсказаний\n"
            "/help - показать это сообщение\n\n"
            "Для начала работы нажми на кнопку /predict и отправь мне фото для анализа эмоций.",
            reply_markup=keyboard
        )
        logger.info(f"Отправлено приветственное сообщение пользователю {message.from_user.id}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        try:
            await message.reply(
                "Извини, произошла ошибка при запуске бота. "
                "Пожалуйста, попробуй позже или обратись к администратору."
            )
        except Exception as msg_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")

async def handle_text(message: types.Message):
    """
    Обрабатывает обычные текстовые сообщения.
    """
    logger.info(f"Получено текстовое сообщение от пользователя {message.from_user.id}")
    
    try:
        keyboard = get_main_keyboard()
        
        await message.reply(
            "Я получил твое сообщение, но не знаю, что с ним делать.\n"
            "Используй кнопки внизу или команду /predict для создания нового предсказания.",
            reply_markup=keyboard
        )
        logger.info(f"Отправлен ответ на текстовое сообщение пользователю {message.from_user.id}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке текстового сообщения: {e}")