"""
Тестирование пользовательских операций в ML Service.

Тесты для проверки работы с пользователями, включая:
- Создание пользователей
- Получение информации о пользователе
- Обновление пользовательских данных
- Проверка работы аутентификации и токенов
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


class UserTester:
    """Класс для тестирования пользовательских операций в ML Service."""

    def __init__(self):
        self.base_url = BASE_URL
        self.api_prefix = API_PREFIX
        self.token = None
        self.username = None
        self.password = None
        self.email = None
        self.user_id = None
        self.tokens = {}

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
        auth: bool = False,
        specific_token: Optional[str] = None
    ) -> requests.Response:
        """Выполняет HTTP-запрос к API."""
        # Добавляем префикс API к эндпоинту, кроме случая, когда эндпоинт уже начинается с префикса или это /health
        if not endpoint.startswith(self.api_prefix) and endpoint != "/health":
            endpoint = f"{self.api_prefix}{endpoint}"
            
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if auth:
            token = specific_token if specific_token else self.token
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
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

    def test_create_user(self) -> bool:
        """Тестирует создание нового пользователя."""
        print("\n=== Тест 1: Создание нового пользователя ===")
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
            print(f"Статус код: {response.status_code}")
            print(f"Ответ: {response.json()}")
            
            if response.status_code == 200:
                print(f"Пользователь создан: {self.username}")
                # Сохраняем ID пользователя, если он есть в ответе
                user_data = response.json()
                if "id" in user_data:
                    self.user_id = user_data["id"]
                return True
            else:
                print(f"Ошибка создания пользователя: {response.json()}")
                return False
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            return False

    def test_login(self) -> bool:
        """Тестирует аутентификацию и получение токена."""
        print("\n=== Тест 2: Аутентификация и получение токена ===")
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
            print(f"Статус код: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                self.token = response_data.get("access_token")
                print(f"Токен получен: {self.token[:10]}...")
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

    def test_create_multiple_users(self, count: int = 3) -> bool:
        """Тестирует создание нескольких пользователей и хранит их токены."""
        print(f"\n=== Тест 3: Создание {count} пользователей ===")
        success_count = 0
        
        for i in range(count):
            username = self.generate_random_username()
            password = f"password{i+1}"
            email = f"{username}@example.com"
            
            try:
                user_data = {
                    "username": username,
                    "password": password,
                    "email": email
                }
                response = self.make_request("POST", "/users", data=user_data)
                
                if response.status_code == 200:
                    print(f"Пользователь {i+1} создан: {username}")
                    
                    # Получаем токен для созданного пользователя
                    auth_data = {
                        "username": username, 
                        "password": password
                    }
                    # Используем API префикс для токена
                    token_url = f"{self.base_url}{self.api_prefix}/token"
                    token_response = requests.post(
                        token_url,
                        data=auth_data,  # Отправляем как form data, не как JSON
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=API_TIMEOUT
                    )
                    
                    print(f"Статус код авторизации для {username}: {token_response.status_code}")
                    
                    if token_response.status_code == 200:
                        token = token_response.json().get("access_token")
                        self.tokens[username] = {
                            "token": token,
                            "password": password,
                            "email": email
                        }
                        success_count += 1
                    else:
                        print(f"Ошибка получения токена для пользователя {username}")
                else:
                    print(f"Ошибка создания пользователя {i+1}: {response.json()}")
            except Exception as e:
                print(f"Ошибка при создании пользователя {i+1}: {e}")
        
        print(f"Успешно создано {success_count} из {count} пользователей")
        return success_count == count

    def test_user_token_validity(self) -> bool:
        """Тестирует валидность токенов для созданных пользователей."""
        print("\n=== Тест 4: Проверка валидности токенов ===")
        if not self.tokens:
            print("Нет токенов для проверки")
            return False
        
        success_count = is_failed = 0
        for username, user_data in self.tokens.items():
            token = user_data["token"]
            
            try:
                # Проверяем токен, делая запрос на получение баланса
                response = self.make_request("GET", "/balance", auth=True, specific_token=token)
                
                if response.status_code == 200:
                    print(f"Токен пользователя {username} валиден")
                    success_count += 1
                else:
                    print(f"Токен пользователя {username} невалиден: {response.json()}")
                    is_failed = True
            except Exception as e:
                print(f"Ошибка при проверке токена пользователя {username}: {e}")
                is_failed = True
        
        # Проверяем также неверный токен
        try:
            invalid_token = "invalid_token_for_testing"
            response = self.make_request("GET", "/balance", auth=True, specific_token=invalid_token)
            
            if response.status_code != 200:
                print("Правильно отклонен неверный токен")
            else:
                print("Ошибка: принят неверный токен")
                is_failed = True
        except Exception as e:
            print(f"Ошибка при проверке неверного токена: {e}")
        
        print(f"Успешно проверено {success_count} из {len(self.tokens)} токенов")
        return success_count == len(self.tokens) and not is_failed

    def test_invalid_login(self) -> bool:
        """Тестирует обработку неверных учетных данных при входе."""
        print("\n=== Тест 5: Обработка неверных учетных данных ===")
        
        # Тест с неверным паролем
        try:
            auth_data = {
                "username": self.username, 
                "password": "wrong_password"
            }
            # Используем API префикс для токена
            token_url = f"{self.base_url}{self.api_prefix}/token"
            response = requests.post(
                token_url,
                data=auth_data,  # Отправляем как form data, не как JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=API_TIMEOUT
            )
            
            if response.status_code != 200:
                print(f"Правильно отклонен неверный пароль (код: {response.status_code})")
            else:
                print("Ошибка: принят неверный пароль")
                return False
        except Exception as e:
            print(f"Ошибка при проверке неверного пароля: {e}")
            return False
        
        # Тест с несуществующим пользователем
        try:
            auth_data = {
                "username": "nonexistent_user", 
                "password": "some_password"
            }
            # Используем API префикс для токена
            token_url = f"{self.base_url}{self.api_prefix}/token"
            response = requests.post(
                token_url,
                data=auth_data,  # Отправляем как form data, не как JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=API_TIMEOUT
            )
            
            if response.status_code != 200:
                print(f"Правильно отклонен несуществующий пользователь (код: {response.status_code})")
                return True
            else:
                print("Ошибка: принят несуществующий пользователь")
                return False
        except Exception as e:
            print(f"Ошибка при проверке несуществующего пользователя: {e}")
            return False

    def test_access_without_token(self) -> bool:
        """Тестирует доступ к защищенным ресурсам без токена."""
        print("\n=== Тест 6: Доступ к защищенным ресурсам без токена ===")
        
        endpoints = [
            "/balance",
            "/transactions",
            "/predictions"
        ]
        
        success_count = 0
        for endpoint in endpoints:
            try:
                # Добавляем префикс API к эндпоинту
                full_endpoint = f"{self.api_prefix}{endpoint}"
                # Запрос без токена
                response = requests.get(
                    f"{self.base_url}{full_endpoint}",
                    timeout=API_TIMEOUT
                )
                
                if response.status_code in [401, 403]:
                    print(f"Правильно отклонен доступ к {endpoint} без токена (код: {response.status_code})")
                    success_count += 1
                else:
                    print(f"Ошибка: разрешен доступ к {endpoint} без токена (код: {response.status_code})")
            except Exception as e:
                print(f"Ошибка при проверке доступа к {endpoint} без токена: {e}")
        
        print(f"Успешно проверено {success_count} из {len(endpoints)} эндпоинтов")
        return success_count == len(endpoints)

    def run_all_tests(self) -> Dict[str, bool]:
        """Запускает все тесты и возвращает результаты."""
        results = {}
        
        # Тест 1: Создание пользователя
        results["create_user"] = self.test_create_user()
        
        # Если пользователь не создан, останавливаем тесты
        if not results["create_user"]:
            print("Ошибка создания пользователя. Тесты остановлены.")
            return results
        
        # Тест 2: Аутентификация и получение токена
        results["login"] = self.test_login()
        
        # Если не получилось залогиниться, продолжаем другие тесты
        if not results["login"]:
            print("Ошибка аутентификации. Пропускаем тесты, требующие токен.")
        
        # Тест 3: Создание нескольких пользователей
        results["create_multiple_users"] = self.test_create_multiple_users()
        
        # Тест 4: Проверка валидности токенов
        if results["create_multiple_users"]:
            results["token_validity"] = self.test_user_token_validity()
        else:
            results["token_validity"] = False
            print("Пропуск проверки токенов: не созданы тестовые пользователи")
        
        # Тест 5: Обработка неверных учетных данных
        results["invalid_login"] = self.test_invalid_login()
        
        # Тест 6: Доступ к защищенным ресурсам без токена
        results["access_without_token"] = self.test_access_without_token()
        
        # Печатаем общие результаты
        print("\n=== Общие результаты тестирования пользователей ===")
        for test_name, result in results.items():
            status = "УСПЕШНО" if result else "ОШИБКА"
            print(f"{test_name}: {status}")
        
        return results


if __name__ == "__main__":
    tester = UserTester()
    test_results = tester.run_all_tests()
    
    # Подсчет успешных тестов
    successful_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    success_rate = (successful_tests / total_tests) * 100
    
    print(f"\nУспешно пройдено {successful_tests} из {total_tests} тестов ({success_rate:.1f}%)")
    
    if successful_tests == total_tests:
        print("[OK] Все тесты пользовательских операций пройдены успешно! Система управления пользователями работает корректно.")
    else:
        print("[FAIL] Некоторые тесты пользовательских операций не пройдены. Система управления пользователями может работать некорректно.") 