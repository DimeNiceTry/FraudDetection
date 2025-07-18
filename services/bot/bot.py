"""
Главный файл Telegram бота.
"""
import os
import logging
import asyncio
import socket
import requests
import time
import sys
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Command
from aiogram.utils import exceptions

from services import wait_for_db, wait_for_rabbitmq
from handlers import (
    send_welcome,
    handle_text,
    PredictionStates,
    cmd_predict,
    cancel_prediction,
    process_photo,
    cmd_prediction_status, 
    cmd_prediction_history,
    cmd_balance,
    BalanceStates,
    cmd_topup,
    process_topup_amount,
    cancel_topup,
    process_prediction_callback
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not API_TOKEN:
    logger.error("Не указан токен API Telegram")
    exit(1)

# Список возможных URL для Telegram API
API_URLS = [
    os.getenv("TELEGRAM_API_URL", "http://api.telegram.org/bot{token}/{method}"),
    "http://api.telegram.org/bot{token}/{method}",
    "https://api.telegram.org/bot{token}/{method}",
    "http://149.154.167.220/bot{token}/{method}",
    "https://149.154.167.220/bot{token}/{method}",
    "http://149.154.167.99/bot{token}/{method}",
    "https://149.154.167.99/bot{token}/{method}"
]

# Проверка доступности Telegram API напрямую через requests
logger.info("Проверка доступности Telegram API через различные URL...")
working_url = None

for api_url in API_URLS:
    try:
        test_url = api_url.format(token=API_TOKEN, method="getMe")
        logger.info(f"Тестирование URL: {test_url}")
        
        # Отключаем проверку SSL для тестов
        response = requests.get(test_url, timeout=5, verify=False)
        
        if response.status_code == 200:
            logger.info(f"URL {test_url} работает! Код статуса: {response.status_code}")
            working_url = api_url
            break
        else:
            logger.warning(f"URL {test_url} не работает. Код статуса: {response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка при тестировании URL {api_url}: {e}")

# Если ни один URL не работает, используем стандартный
if not working_url:
    logger.warning("Ни один из URL не работает, используем стандартный API URL")
    working_url = API_URLS[0]
    
logger.info(f"Используем URL для API Telegram: {working_url}")

# Инициализация бота и диспетчера с прямым указанием URL
bot = Bot(token=API_TOKEN, validate_token=False)
bot._base_url = working_url
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация обработчиков команд
dp.register_message_handler(send_welcome, commands=['start', 'help'])
dp.register_message_handler(cmd_predict, commands=['predict'])
dp.register_message_handler(cancel_prediction, commands=['cancel'], state='*')
dp.register_message_handler(cmd_balance, commands=['balance'])
dp.register_message_handler(cmd_topup, commands=['topup'])
dp.register_message_handler(cmd_prediction_status, commands=['status'])
dp.register_message_handler(cmd_prediction_history, commands=['history'])

# Регистрация обработчиков колбэков
dp.register_callback_query_handler(process_prediction_callback, lambda c: c.data.startswith('prediction:') or c.data == 'refresh_history')

# Регистрация обработчиков состояний
dp.register_message_handler(
    process_photo, 
    content_types=types.ContentTypes.PHOTO,
    state=PredictionStates.waiting_for_photo
)

dp.register_message_handler(
    process_topup_amount,
    state=BalanceStates.waiting_for_amount
)

dp.register_message_handler(cancel_topup, commands=['cancel'], state=BalanceStates.waiting_for_amount)

# Обработчик для текстовых сообщений, когда нет активных состояний
dp.register_message_handler(handle_text, content_types=types.ContentTypes.TEXT)

async def on_startup(dp):
    """
    Выполняется при запуске бота.
    """
    logger.info("Запуск бота...")
    
    # Проверяем соединение с Telegram API
    try:
        logger.info("Проверка соединения с Telegram API...")
        me = await bot.get_me()
        logger.info(f"Подключено как: {me.username}")
    except exceptions.NetworkError as e:
        logger.error(f"Не удалось подключиться к Telegram API: {e}")
        # Пробуем другие URL
        for api_url in API_URLS:
            if api_url != working_url:
                try:
                    logger.info(f"Пробуем альтернативный URL: {api_url}")
                    bot._base_url = api_url
                    me = await bot.get_me()
                    logger.info(f"Подключено через альтернативный URL как: {me.username}")
                    working_url = api_url
                    break
                except Exception as e2:
                    logger.error(f"Не удалось подключиться через URL {api_url}: {e2}")
        else:
            logger.error("Не удалось подключиться ни к одному URL Telegram API")
    
    # Ожидаем доступности базы данных с повторными попытками
    db_attempts = 0
    while db_attempts < 5:
        if wait_for_db():
            logger.info("Успешное подключение к базе данных")
            break
        db_attempts += 1
        logger.warning(f"Попытка подключения к базе данных {db_attempts}/5 не удалась, повторяем...")
        await asyncio.sleep(5)
    else:
        logger.error("Не удалось подключиться к базе данных после нескольких попыток")
        return
    
    # Ожидаем доступности RabbitMQ с повторными попытками
    rmq_attempts = 0
    while rmq_attempts < 5:
        if wait_for_rabbitmq():
            logger.info("Успешное подключение к RabbitMQ")
            break
        rmq_attempts += 1
        logger.warning(f"Попытка подключения к RabbitMQ {rmq_attempts}/5 не удалась, повторяем...")
        await asyncio.sleep(5)
    else:
        logger.error("Не удалось подключиться к RabbitMQ после нескольких попыток")
        return
    
    logger.info("Бот успешно запущен")

def main():
    """
    Основная функция для запуска бота.
    """
    try:
        # Отключаем предупреждения SSL для всех запросов
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Настройка для requests
        requests.packages.urllib3.disable_warnings()
        
        logger.info("Запуск поллинга Telegram...")
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        time.sleep(10)  # Ждем 10 секунд перед выходом
        raise

if __name__ == '__main__':
    # Повторно запускаем бота при ошибках
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"Бот упал с ошибкой: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем")
            sys.exit(0)