#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов ML Service.

Запускает все типы тестов и выводит общий результат:
1. Тесты работоспособности системы
2. Тесты транзакций
3. Тесты пользовательских операций
"""

import os
import sys
import time
import subprocess
from typing import Dict, List, Tuple

# Общие настройки
TESTS = [
    {"file": "test_system.py", "name": "Общие тесты системы"},
    {"file": "test_transactions.py", "name": "Тесты транзакций"},
    {"file": "test_users.py", "name": "Тесты пользовательских операций"}
]


def check_service_availability() -> bool:
    """Проверяет доступность сервиса перед запуском тестов."""
    import requests
    try:
        # Проверяем доступность сервиса
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("Сервис доступен по эндпоинту: /health")
            status = response.json().get("status")
            return status == "healthy" or status == "ok"
            
        # Если health check не работает, проверяем доступность API через docs
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("API доступно, но эндпоинт проверки здоровья не найден.")
            return True
            
        return False
    except Exception as e:
        print(f"Ошибка при проверке доступности: {e}")
        return False


def wait_for_service(max_attempts: int = 10, delay: int = 5) -> bool:
    """Ожидает готовности сервиса с повторными попытками."""
    print("Проверка доступности ML Service...")
    
    for attempt in range(1, max_attempts + 1):
        if check_service_availability():
            print(f"[OK] ML Service доступен и готов к тестированию (попытка {attempt}/{max_attempts})")
            return True
        
        print(f"[WAIT] ML Service не доступен. Ожидание... (попытка {attempt}/{max_attempts})")
        time.sleep(delay)
    
    print("[FAIL] ML Service не доступен после нескольких попыток. Убедитесь, что система запущена.")
    return False


def run_test(test_file: str) -> Tuple[bool, str]:
    """Запускает отдельный тестовый скрипт и возвращает результат."""
    try:
        print(f"\n\n{'=' * 60}")
        print(f"Запуск {test_file}")
        print(f"{'=' * 60}\n")
        
        # Запускаем тест с перенаправлением вывода в консоль (не захватываем stderr)
        result = subprocess.run([sys.executable, test_file], text=True)
        
        # Запускаем тест еще раз для определения статуса, захватывая вывод
        result_capture = subprocess.run([sys.executable, test_file], capture_output=True, text=True)
        output = result_capture.stdout + result_capture.stderr
        
        # Определяем статус по возвращаемому коду и анализу вывода
        if result.returncode == 0:
            lines = output.strip().split('\n')
            # Ищем строки успеха в выводе
            success = any(("[OK]" in line and "успешно" in line) or 
                         ("Успешно пройдено" in line and "из" in line and "100.0%" in line)
                         for line in lines[-10:])
            return success, output
        else:
            return False, output
    except Exception as e:
        return False, f"Ошибка при запуске теста {test_file}: {str(e)}"


def main():
    """Основная функция запуска всех тестов."""
    print("\n" + "=" * 80)
    print(f"{'ЗАПУСК ВСЕХ ТЕСТОВ ML SERVICE':^80}")
    print("=" * 80 + "\n")
    
    # Проверяем доступность сервиса
    if not wait_for_service():
        sys.exit(1)
    
    results = {}
    outputs = {}
    
    # Запускаем каждый тест
    for test in TESTS:
        test_file = test["file"]
        test_name = test["name"]
        
        success, output = run_test(test_file)
        results[test_file] = success
        outputs[test_file] = output
        
        # Печатаем результат теста
        status = "УСПЕШНО" if success else "ОШИБКА"
        print(f"\n> {test_name}: {status}")
    
    # Общий результат всех тестов
    total_tests = len(TESTS)
    successful_tests = sum(1 for result in results.values() if result)
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print("\n" + "=" * 80)
    print(f"{'РЕЗУЛЬТАТЫ ТЕСТОВ':^80}")
    print("=" * 80)
    
    # Выводим результаты по каждому тесту
    for i, test in enumerate(TESTS):
        test_file = test["file"]
        test_name = test["name"]
        status = "[OK]" if results[test_file] else "[FAIL]"
        print(f"{i+1}. {test_name}: {status}")
    
    print("-" * 80)
    print(f"Успешно пройдено {successful_tests} из {total_tests} тестов ({success_rate:.1f}%)")
    
    # Общий результат
    if successful_tests == total_tests:
        print("\n[OK] ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ! СИСТЕМА РАБОТАЕТ КОРРЕКТНО.")
    else:
        print("\n[FAIL] НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ. СИСТЕМА МОЖЕТ РАБОТАТЬ НЕКОРРЕКТНО.")
        
        # Выводим детали проваленных тестов
        print("\nДетали проваленных тестов:")
        for test in TESTS:
            test_file = test["file"]
            if not results[test_file]:
                print(f"\n--- {test['name']} ({test_file}) ---")
                # Находим строки с ошибками
                lines = outputs[test_file].split('\n')
                error_lines = [line for line in lines if "ОШИБКА" in line or "ошибка" in line or "Error" in line or "error" in line]
                if error_lines:
                    for line in error_lines[-10:]:  # Показываем только последние 10 ошибок
                        print(line)
                else:
                    print("Причина ошибки не найдена в выводе")
    
    # Возвращаем статус для использования в CI/CD
    return 0 if successful_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main()) 