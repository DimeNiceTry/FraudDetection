#!/usr/bin/env python3
"""
Скрипт для проверки доступности API Telegram.
"""
import os
import sys
import requests
import time
import logging
import urllib3

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    sys.exit(1)

# Список возможных URL для API Telegram
API_URLS = [
    "http://api.telegram.org/bot{token}/{method}",
    "https://api.telegram.org/bot{token}/{method}",
    "http://149.154.167.220/bot{token}/{method}",
    "https://149.154.167.220/bot{token}/{method}",
    "http://149.154.167.99/bot{token}/{method}",
    "https://149.154.167.99/bot{token}/{method}"
]

def check_api_urls():
    """
    Проверяет доступность различных URL для API Telegram.
    
    Returns:
        str: Рабочий URL или None, если ни один не работает
    """
    for api_url in API_URLS:
        try:
            test_url = api_url.format(token=API_TOKEN, method="getMe")
            logger.info(f"Тестирование URL: {test_url}")
            
            # Отключаем проверку SSL для тестов
            response = requests.get(test_url, timeout=10, verify=False)
            
            if response.status_code == 200:
                logger.info(f"URL {test_url} работает! Код статуса: {response.status_code}")
                logger.info(f"Ответ: {response.text}")
                return api_url
            else:
                logger.warning(f"URL {test_url} не работает. Код статуса: {response.status_code}")
                logger.warning(f"Ответ: {response.text}")
        except Exception as e:
            logger.error(f"Ошибка при тестировании URL {api_url}: {e}")
    
    return None

def main():
    """
    Основная функция скрипта.
    """
    logger.info("Начинаем проверку доступности API Telegram...")
    working_url = check_api_urls()
    
    if working_url:
        logger.info(f"Найден рабочий URL для API Telegram: {working_url}")
        sys.exit(0)
    else:
        logger.error("Не удалось найти работающий URL для API Telegram!")
        sys.exit(1)

if __name__ == "__main__":
    main() 