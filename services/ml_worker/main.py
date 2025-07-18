#!/usr/bin/env python3
"""
Точка входа для ML Worker.
"""
import os
import sys
import logging
import socket

# Добавление корневого каталога в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from worker.services.worker_service import run_worker, WORKER_ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"Запуск ML Worker с ID: {WORKER_ID}")
    if not run_worker():
        logger.error("Ошибка при запуске ML Worker")
        sys.exit(1) 