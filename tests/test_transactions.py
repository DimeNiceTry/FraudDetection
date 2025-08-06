"""
Тестирование транзакций в ML Service.

Тесты для проверки работы с балансом и транзакциями пользователей, включая:
- Создание тестового пользователя
- Пополнение баланса разными суммами
- Списание кредитов с баланса
- Проверка истории транзакций
- Проверка наличия транзакций разных типов
"""

import requests
import time
import random
import string
import json
from typing import Dict, Any, Optional, List, Tuple

# Базовые настройки для тестов
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"  # Префикс API
API_TIMEOUT = 10


class TransactionTester:
    """Класс для тестирования транзакций в ML Service."""

    def __init__(self):
        self.base_url = BASE_URL
        self.api_prefix = API_PREFIX
        self.token = None
        self.username = None
        self.password = None
        self.email = None
        self.initial_balance = 0.0

    def generate_random_username(self, prefix="testuser") -> str:
        """Генерирует случайное имя пользователя."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{prefix}_{random_suffix}"

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        auth: bool = False
    ) -> requests.Response:
        """Выполняет HTTP-запрос к API."""
        # Добавляем префикс API к эндпоинту, кроме случая, когда эндпоинт уже начинается с префикса или это /health
        if not endpoint.startswith(self.api_prefix) and endpoint != "/health":
            endpoint = f"{self.api_prefix}{endpoint}"
            
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        if method.upper() == "GET":
            response = requests.get(url, params=params, headers=headers, timeout=API_TIMEOUT)
        elif method.upper() == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, json=data, headers=headers, timeout=API_TIMEOUT)
        elif method.upper() == "PUT":
            headers["Content-Type"] = "application/json"
            response = requests.put(url, json=data, headers=headers, timeout=API_TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=API_TIMEOUT)
        else:
            raise ValueError(f"Неподдерживаемый HTTP метод: {method}")
        
        return response

    def setup_test_user(self) -> bool:
        """Создает или использует тестового пользователя."""
        print("\n=== Настройка тестового пользователя ===")
        
        # Сначала попробуем использовать существующего тестового пользователя
        self.username = "test"
        self.password = "test"
        
        if self.login():
            print("Используем существующего тестового пользователя: test")
            return True
        
        # Если не удалось войти, создаем нового пользователя
        self.username = self.generate_random_username()
        self.password = "testpassword123"
        self.email = f"{self.username}@example.com"
        
        try:
            user_data = {
                "username": self.username,
                "password": self.password,
                "email": self.email
            }
            response = self.make_request("POST", "/users", data=user_data)
            
            if response.status_code == 200:
                print(f"Создан новый тестовый пользователь: {self.username}")
                return self.login()
            else:
                print(f"Ошибка создания пользователя: {response.json()}")
                return False
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            return False

    def login(self) -> bool:
        """Выполняет аутентификацию и получает токен."""
        try:
            # Используем form-data для отправки данных авторизации
            token_url = f"{self.base_url}{self.api_prefix}/token"
            
            # Вывод для диагностики
            print(f"Попытка авторизации для пользователя: {self.username}")
            
            # Используем правильный формат данных для API
            auth_data = {
                "username": self.username, 
                "password": self.password
            }
            
            response = requests.post(
                token_url,
                data=auth_data,  # Отправляем как form data, не как JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=API_TIMEOUT
            )
            
            print(f"Статус код авторизации: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                self.token = response_data.get("access_token")
                print(f"Аутентификация успешна. Получен токен: {self.token[:10]}...")
                return True
            else:
                print(f"Ошибка аутентификации: {response.text}")
                # Дополнительная отладочная информация
                print(f"Используемый URL: {token_url}")
                print(f"Отправленные данные: {auth_data}")
                return False
        except Exception as e:
            print(f"Ошибка при аутентификации: {e}")
            return False

    def get_balance(self) -> Tuple[bool, float]:
        """Получает текущий баланс пользователя."""
        try:
            response = self.make_request("GET", "/balance", auth=True)
            
            if response.status_code == 200:
                balance = response.json().get("balance")
                return True, balance
            else:
                print(f"Ошибка получения баланса: {response.json()}")
                return False, 0
        except Exception as e:
            print(f"Ошибка при получении баланса: {e}")
            return False, 0

    def test_get_initial_balance(self) -> bool:
        """Получает и сохраняет начальный баланс пользователя."""
        print("\n=== Тест 1: Получение начального баланса ===")
        success, balance = self.get_balance()
        
        if success:
            self.initial_balance = balance
            print(f"Начальный баланс: {self.initial_balance} кредитов")
            return True
        else:
            print("Ошибка получения начального баланса")
            return False

    def test_top_up_small_amount(self, amount: float = 10.0) -> bool:
        """Тестирует пополнение баланса на небольшую сумму."""
        print(f"\n=== Тест 2: Пополнение баланса на небольшую сумму ({amount} кредитов) ===")
        try:
            data = {
                "amount": amount,
                "description": "Тестовое пополнение на небольшую сумму"
            }
            response = self.make_request("POST", "/balance/topup", data=data, auth=True)
            
            if response.status_code == 200:
                print(f"Баланс успешно пополнен на {amount} кредитов")
                
                # Проверяем обновленный баланс
                success, new_balance = self.get_balance()
                if success:
                    expected_balance = self.initial_balance + amount
                    print(f"Новый баланс: {new_balance} кредитов")
                    print(f"Ожидаемый баланс: {expected_balance} кредитов")
                    
                    if abs(new_balance - expected_balance) < 0.001:  # Учитываем возможные ошибки округления
                        print("Баланс обновлен корректно")
                        self.initial_balance = new_balance  # Обновляем начальный баланс
                        return True
                    else:
                        print("Баланс обновлен некорректно")
                        return False
                else:
                    print("Ошибка получения обновленного баланса")
                    return False
            else:
                print(f"Ошибка пополнения баланса: {response.json()}")
                return False
        except Exception as e:
            print(f"Ошибка при пополнении баланса: {e}")
            return False

    def test_top_up_large_amount(self, amount: float = 1000.0) -> bool:
        """Тестирует пополнение баланса на большую сумму."""
        print(f"\n=== Тест 3: Пополнение баланса на большую сумму ({amount} кредитов) ===")
        try:
            data = {
                "amount": amount,
                "description": "Тестовое пополнение на большую сумму"
            }
            response = self.make_request("POST", "/balance/topup", data=data, auth=True)
            
            if response.status_code == 200:
                print(f"Баланс успешно пополнен на {amount} кредитов")
                
                # Проверяем обновленный баланс
                success, new_balance = self.get_balance()
                if success:
                    expected_balance = self.initial_balance + amount
                    print(f"Новый баланс: {new_balance} кредитов")
                    print(f"Ожидаемый баланс: {expected_balance} кредитов")
                    
                    if abs(new_balance - expected_balance) < 0.001:
                        print("Баланс обновлен корректно")
                        self.initial_balance = new_balance
                        return True
                    else:
                        print("Баланс обновлен некорректно")
                        return False
                else:
                    print("Ошибка получения обновленного баланса")
                    return False
            else:
                print(f"Ошибка пополнения баланса: {response.json()}")
                return False
        except Exception as e:
            print(f"Ошибка при пополнении баланса: {e}")
            return False

    def test_make_prediction_payment(self) -> bool:
        """Тестирует списание средств при выполнении предсказания."""
        print("\n=== Тест 4: Списание средств при выполнении предсказания ===")
        try:
            # Получаем баланс до предсказания
            success, balance_before = self.get_balance()
            if not success:
                print("Ошибка получения баланса перед предсказанием")
                return False
            
            print(f"Баланс до предсказания: {balance_before} кредитов")
            
            # Отправляем запрос на предсказание
            data = {
                "data": {
                    "text": "Тестовый текст для предсказания"
                }
            }
            response = self.make_request("POST", "/predictions/predict", data=data, auth=True)
            
            if response.status_code == 202:
                prediction_id = response.json().get("prediction_id")
                print(f"Запрос на предсказание отправлен. ID: {prediction_id}")
                
                # Ждем завершения предсказания
                time.sleep(5)
                
                # Получаем баланс после предсказания
                success, balance_after = self.get_balance()
                if not success:
                    print("Ошибка получения баланса после предсказания")
                    return False
                
                print(f"Баланс после предсказания: {balance_after} кредитов")
                
                # Проверяем, что средства были списаны
                if balance_after < balance_before:
                    amount_charged = balance_before - balance_after
                    print(f"Списано {amount_charged} кредитов за предсказание")
                    self.initial_balance = balance_after
                    return True
                else:
                    print("Средства не были списаны за предсказание")
                    return False
            else:
                print(f"Ошибка отправки запроса на предсказание: {response.json()}")
                return False
        except Exception as e:
            print(f"Ошибка при тестировании списания средств: {e}")
            return False

    def test_transaction_history(self) -> bool:
        """Тестирует получение истории транзакций."""
        print("\n=== Тест 5: Получение истории транзакций ===")
        try:
            response = self.make_request("GET", "/transactions", auth=True)
            
            if response.status_code == 200:
                transactions = response.json()
                print(f"Получено {len(transactions)} транзакций")
                
                if transactions:
                    # Выводим информацию о нескольких последних транзакциях
                    for i, tx in enumerate(transactions[:5]):
                        print(f"{i+1}. Тип: {tx.get('type')}, Сумма: {tx.get('amount')}, Дата: {tx.get('created_at')}")
                    
                    # Проверяем наличие разных типов транзакций
                    top_up_transactions = [tx for tx in transactions if tx.get('type') == 'topup']
                    payment_transactions = [tx for tx in transactions if tx.get('type') == 'payment']
                    
                    print(f"Найдено транзакций пополнения: {len(top_up_transactions)}")
                    print(f"Найдено транзакций оплаты: {len(payment_transactions)}")
                    
                    if top_up_transactions and payment_transactions:
                        print("В истории есть транзакции пополнения и оплаты")
                        return True
                    else:
                        if not top_up_transactions:
                            print("В истории нет транзакций пополнения")
                        if not payment_transactions:
                            print("В истории нет транзакций оплаты")
                        return False
                else:
                    print("История транзакций пуста")
                    return False
            else:
                print(f"Ошибка получения истории транзакций: {response.json()}")
                return False
        except Exception as e:
            print(f"Ошибка при получении истории транзакций: {e}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Запускает все тесты и возвращает результаты."""
        results = {}
        
        # Настраиваем тестового пользователя
        if not self.setup_test_user():
            print("Ошибка настройки тестового пользователя. Тесты остановлены.")
            return {"setup_test_user": False}
        
        results["setup_test_user"] = True
        
        # Тест 1: Получение начального баланса
        results["get_initial_balance"] = self.test_get_initial_balance()
        
        # Тест 2: Пополнение баланса на небольшую сумму
        results["top_up_small_amount"] = self.test_top_up_small_amount()
        
        # Тест 3: Пополнение баланса на большую сумму
        results["top_up_large_amount"] = self.test_top_up_large_amount()
        
        # Тест 4: Списание средств при выполнении предсказания
        results["make_prediction_payment"] = self.test_make_prediction_payment()
        
        # Тест 5: Получение истории транзакций
        results["transaction_history"] = self.test_transaction_history()
        
        # Печатаем общие результаты
        print("\n=== Общие результаты тестирования транзакций ===")
        for test_name, result in results.items():
            status = "УСПЕШНО" if result else "ОШИБКА"
            print(f"{test_name}: {status}")
        
        return results


if __name__ == "__main__":
    tester = TransactionTester()
    test_results = tester.run_all_tests()
    
    # Подсчет успешных тестов
    successful_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    success_rate = (successful_tests / total_tests) * 100
    
    print(f"\nУспешно пройдено {successful_tests} из {total_tests} тестов ({success_rate:.1f}%)")
    
    if successful_tests == total_tests:
        print("[OK] Все тесты транзакций пройдены успешно! Система обработки транзакций работает корректно.")
    else:
        print("[FAIL] Некоторые тесты транзакций не пройдены. Система обработки транзакций работает некорректно или не полностью функциональна.") 