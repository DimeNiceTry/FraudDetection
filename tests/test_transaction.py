#!/usr/bin/env python3
"""
Скрипт для тестирования API поиска злоумышленных транзакций.
"""

import requests
import json
import time
from datetime import datetime

# URL API
API_URL = "http://localhost:8000"

# Тестовые учетные данные
USERNAME = "test"
PASSWORD = "test"

def get_token():
    """Получение токена авторизации."""
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={"username": USERNAME, "password": PASSWORD}
        )
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]
    except Exception as e:
        print(f"Ошибка при получении токена: {e}")
        return None

def predict_transaction(token, transaction_data):
    """Отправка транзакции на анализ."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"data": {"transaction": transaction_data}}
    
    try:
        response = requests.post(
            f"{API_URL}/predictions/predict",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при отправке транзакции: {e}")
        return None

def get_prediction_result(token, prediction_id):
    """Получение результатов анализа транзакции."""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{API_URL}/predictions/{prediction_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при получении результатов: {e}")
        return None

def main():
    # Получаем токен
    token = get_token()
    if not token:
        print("Не удалось получить токен авторизации")
        return
    
    print("Токен авторизации получен успешно")
    
    # Пример данных транзакции
    # Здесь должны быть признаки, которые использовались при обучении модели
    # Ниже приведен пример, который нужно заменить реальными признаками
    transaction = {
        "id": "tx123456",
        "amount": 1000.00,
        "hour": 14,
        "day": 3,
        "month": 7,
        "origin_account": "acc123",
        "dest_account": "acc456",
        "old_balance_orig": 5000.00,
        "new_balance_orig": 4000.00,
        "old_balance_dest": 1000.00,
        "new_balance_dest": 2000.00,
        "is_flagged": 0,
    }
    
    # Отправляем транзакцию на анализ
    print("Отправка транзакции на анализ...")
    prediction = predict_transaction(token, transaction)
    
    if not prediction:
        print("Не удалось отправить транзакцию на анализ")
        return
    
    prediction_id = prediction["prediction_id"]
    print(f"Транзакция отправлена. ID предсказания: {prediction_id}")
    
    # Ожидаем обработки
    print("Ожидание результатов анализа...")
    result = None
    max_attempts = 10
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        result = get_prediction_result(token, prediction_id)
        
        if result and result.get("status") != "pending":
            break
            
        print(f"Ожидание... Попытка {attempts}/{max_attempts}")
        time.sleep(1)
    
    # Выводим результат
    if result and result.get("status") == "completed":
        print("\nРезультат анализа транзакции:")
        print(f"Предсказание: {result['result']['prediction']}")
        print(f"Вероятность мошенничества: {result['result'].get('fraud_probability', 0) * 100:.2f}%")
        print(f"Транзакция мошенническая: {'Да' if result['result'].get('is_fraud', False) else 'Нет'}")
        print(f"Уверенность: {result['result'].get('confidence', 0) * 100:.2f}%")
        print(f"Время обработки: {result['result'].get('processing_time', 0):.2f} сек")
        print(f"Обработано воркером: {result['result'].get('worker_id', 'unknown')}")
    else:
        print("\nНе удалось получить результат анализа транзакции или время ожидания истекло")
        print(f"Статус: {result.get('status', 'unknown') if result else 'unknown'}")

if __name__ == "__main__":
    main() 