"""
Юнит-тесты для API-эндпоинтов ML Service.

Эти тесты проверяют работу API-эндпоинтов в изоляции, используя FastAPI TestClient
и моки для внешних зависимостей.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status
import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

try:
    from app.main import app
    from app.api.deps import get_db, get_current_user
    from app.schemas.user import UserCreate, UserLogin, UserResponse
    from app.schemas.transaction import TransactionCreate, TransactionResponse
    from app.schemas.prediction import PredictionCreate, PredictionResponse
    from app.models.user import User
    from app.models.transaction import Transaction
    from app.models.prediction import Prediction
    from app.core.security import create_access_token, verify_access_token
    
    # Флаг для определения доступности реальных модулей
    REAL_MODULES_AVAILABLE = True
except ImportError:
    REAL_MODULES_AVAILABLE = False
    print("Внимание: Реальные модули недоступны. Используются заглушки для тестов.")


# Пропускаем тесты, если модули недоступны
pytestmark = pytest.mark.skipif(not REAL_MODULES_AVAILABLE, reason="Реальные модули недоступны")


# Фикстуры для тестов
@pytest.fixture
def mock_db():
    """Фикстура, создающая мок сессии БД."""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def mock_user():
    """Фикстура, создающая мок пользователя."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = "hashedpassword123"
    user.balance = 100.0
    user.created_at = datetime.now()
    return user


@pytest.fixture
def mock_token(mock_user):
    """Фикстура, создающая тестовый токен."""
    if REAL_MODULES_AVAILABLE:
        token = create_access_token(data={"sub": mock_user.username})
    else:
        token = "test_token"
    return token


@pytest.fixture
def client():
    """Фикстура, создающая клиент для тестирования API."""
    return TestClient(app)


@pytest.fixture
def db_session_override(mock_db):
    """Фикстура для переопределения зависимости БД в FastAPI."""
    def _get_db_override():
        return mock_db
    
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db)


@pytest.fixture
def current_user_override(mock_user):
    """Фикстура для переопределения зависимости текущего пользователя в FastAPI."""
    def _get_current_user_override():
        return mock_user
    
    app.dependency_overrides[get_current_user] = _get_current_user_override
    yield
    app.dependency_overrides.pop(get_current_user)


# Тесты для системных эндпоинтов
class TestSystemEndpoints:
    """Тесты для системных API-эндпоинтов."""
    
    def test_health_endpoint(self, client, db_session_override):
        """Тест эндпоинта проверки работоспособности."""
        # Отправка запроса
        response = client.get("/health")
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}


# Тесты для пользовательских эндпоинтов
class TestUserEndpoints:
    """Тесты для API-эндпоинтов пользователей."""
    
    def test_create_user(self, client, mock_db, mock_user, db_session_override):
        """Тест создания пользователя."""
        # Настройка входных данных
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        }
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Патч для сервиса пользователей
        with patch("app.api.endpoints.users.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.create_user.return_value = UserResponse(
                id=mock_user.id,
                username=mock_user.username,
                email=mock_user.email,
                balance=mock_user.balance,
                created_at=mock_user.created_at
            )
            
            # Отправка запроса
            response = client.post("/users/", json=user_data)
        
        # Проверки
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id"] == mock_user.id
        assert response.json()["username"] == mock_user.username
        assert response.json()["email"] == mock_user.email
        assert "password" not in response.json()
        mock_user_service.create_user.assert_called_once()
    
    def test_create_user_duplicate(self, client, mock_db, mock_user, db_session_override):
        """Тест создания пользователя с уже существующим именем."""
        # Настройка входных данных
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        }
        
        # Патч для сервиса пользователей
        with patch("app.api.endpoints.users.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.create_user.side_effect = ValueError("Username already registered")
            
            # Отправка запроса
            response = client.post("/users/", json=user_data)
        
        # Проверки
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already registered" in response.json()["detail"]
        mock_user_service.create_user.assert_called_once()
    
    def test_login_success(self, client, mock_db, mock_user, mock_token, db_session_override):
        """Тест успешной авторизации пользователя."""
        # Настройка входных данных
        login_data = {
            "username": "testuser",
            "password": "testpassword"
        }
        
        # Патч для сервиса пользователей
        with patch("app.api.endpoints.auth.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.authenticate_user.return_value = mock_user
            
            # Патч для создания токена
            with patch("app.api.endpoints.auth.create_access_token", return_value=mock_token):
                # Отправка запроса
                response = client.post("/auth/login", data=login_data)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access_token"] == mock_token
        assert response.json()["token_type"] == "bearer"
        mock_user_service.authenticate_user.assert_called_once_with(
            login_data["username"], login_data["password"]
        )
    
    def test_login_invalid_credentials(self, client, mock_db, db_session_override):
        """Тест авторизации с неверными учетными данными."""
        # Настройка входных данных
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        
        # Патч для сервиса пользователей
        with patch("app.api.endpoints.auth.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.authenticate_user.return_value = None
            
            # Отправка запроса
            response = client.post("/auth/login", data=login_data)
        
        # Проверки
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]
        mock_user_service.authenticate_user.assert_called_once_with(
            login_data["username"], login_data["password"]
        )
    
    def test_get_current_user(self, client, mock_user, current_user_override):
        """Тест получения текущего пользователя."""
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        
        # Отправка запроса
        response = client.get("/users/me", headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == mock_user.id
        assert response.json()["username"] == mock_user.username
        assert response.json()["email"] == mock_user.email
        assert "password" not in response.json()


# Тесты для эндпоинтов транзакций
class TestTransactionEndpoints:
    """Тесты для API-эндпоинтов транзакций."""
    
    def test_get_balance(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест получения баланса пользователя."""
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        
        # Патч для сервиса транзакций
        with patch("app.api.endpoints.transactions.TransactionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_balance.return_value = mock_user.balance
            
            # Отправка запроса
            response = client.get("/transactions/balance", headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["balance"] == mock_user.balance
        mock_service.get_balance.assert_called_once_with(mock_user.id)
    
    def test_top_up_balance(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест пополнения баланса пользователя."""
        # Настройка входных данных
        data = {
            "amount": 50.0,
            "description": "Тестовое пополнение"
        }
        
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        
        # Патч для сервиса транзакций
        with patch("app.api.endpoints.transactions.TransactionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.top_up_balance.return_value = (mock_user.balance, mock_user.balance + data["amount"], "tx_123")
            
            # Отправка запроса
            response = client.post("/transactions/topup", json=data, headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["previous_balance"] == mock_user.balance
        assert response.json()["current_balance"] == mock_user.balance + data["amount"]
        assert response.json()["transaction_id"] == "tx_123"
        mock_service.top_up_balance.assert_called_once_with(
            mock_user.id, data["amount"], data["description"]
        )
    
    def test_get_transactions(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест получения истории транзакций пользователя."""
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        
        # Создаем мок ответа сервиса
        mock_transaction = MagicMock(spec=Transaction)
        mock_transaction.id = str(uuid.uuid4())
        mock_transaction.user_id = mock_user.id
        mock_transaction.type = "topup"
        mock_transaction.amount = 50.0
        mock_transaction.description = "Тестовое пополнение"
        mock_transaction.created_at = datetime.now()
        
        # Патч для сервиса транзакций
        with patch("app.api.endpoints.transactions.TransactionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_user_transactions.return_value = [mock_transaction] * 5
            
            # Отправка запроса
            response = client.get("/transactions/history", headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 5
        for tx in response.json():
            assert tx["user_id"] == mock_user.id
            assert tx["type"] == "topup"
            assert tx["amount"] == 50.0
            assert tx["description"] == "Тестовое пополнение"
        mock_service.get_user_transactions.assert_called_once_with(mock_user.id)


# Тесты для эндпоинтов предсказаний
class TestPredictionEndpoints:
    """Тесты для API-эндпоинтов предсказаний."""
    
    def test_create_prediction(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест создания предсказания."""
        # Настройка входных данных
        data = {
            "data": {"text": "Тестовый текст"},
            "model_version": "v1.0"
        }
        
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        
        # Создаем мок ответа сервиса
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = str(uuid.uuid4())
        mock_prediction.user_id = mock_user.id
        mock_prediction.status = "pending"
        mock_prediction.data = data["data"]
        mock_prediction.result = None
        mock_prediction.model_version = data["model_version"]
        mock_prediction.created_at = datetime.now()
        mock_prediction.updated_at = datetime.now()
        
        # Патч для сервиса предсказаний
        with patch("app.api.endpoints.predictions.PredictionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.create_prediction.return_value = mock_prediction
            
            # Патч для брокера сообщений (чтобы не пытаться отправить реальное сообщение)
            with patch("app.api.endpoints.predictions.publish_prediction"):
                # Отправка запроса
                response = client.post("/predictions/", json=data, headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["id"] == mock_prediction.id
        assert response.json()["status"] == "pending"
        assert response.json()["data"] == data["data"]
        assert response.json()["model_version"] == data["model_version"]
        mock_service.create_prediction.assert_called_once()
    
    def test_get_prediction(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест получения предсказания по ID."""
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        prediction_id = str(uuid.uuid4())
        
        # Создаем мок ответа сервиса
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = prediction_id
        mock_prediction.user_id = mock_user.id
        mock_prediction.status = "completed"
        mock_prediction.data = {"text": "Тестовый текст"}
        mock_prediction.result = {"prediction": "positive", "confidence": 0.95}
        mock_prediction.model_version = "v1.0"
        mock_prediction.created_at = datetime.now()
        mock_prediction.updated_at = datetime.now()
        
        # Патч для сервиса предсказаний
        with patch("app.api.endpoints.predictions.PredictionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_prediction.return_value = mock_prediction
            
            # Отправка запроса
            response = client.get(f"/predictions/{prediction_id}", headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == prediction_id
        assert response.json()["status"] == "completed"
        assert response.json()["data"] == {"text": "Тестовый текст"}
        assert response.json()["result"] == {"prediction": "positive", "confidence": 0.95}
        mock_service.get_prediction.assert_called_once_with(prediction_id)
    
    def test_get_prediction_not_found(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест получения несуществующего предсказания."""
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        prediction_id = str(uuid.uuid4())
        
        # Патч для сервиса предсказаний
        with patch("app.api.endpoints.predictions.PredictionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_prediction.return_value = None
            
            # Отправка запроса
            response = client.get(f"/predictions/{prediction_id}", headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Prediction not found" in response.json()["detail"]
        mock_service.get_prediction.assert_called_once_with(prediction_id)
    
    def test_get_user_predictions(self, client, mock_user, mock_db, current_user_override, db_session_override):
        """Тест получения всех предсказаний пользователя."""
        # Настройка моков
        headers = {"Authorization": f"Bearer test_token"}
        
        # Создаем мок ответа сервиса
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = str(uuid.uuid4())
        mock_prediction.user_id = mock_user.id
        mock_prediction.status = "pending"
        mock_prediction.data = {"text": "Тестовый текст"}
        mock_prediction.result = None
        mock_prediction.model_version = "v1.0"
        mock_prediction.created_at = datetime.now()
        mock_prediction.updated_at = datetime.now()
        
        # Патч для сервиса предсказаний
        with patch("app.api.endpoints.predictions.PredictionService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_user_predictions.return_value = [mock_prediction] * 5
            
            # Отправка запроса
            response = client.get("/predictions/my", headers=headers)
        
        # Проверки
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 5
        for pred in response.json():
            assert pred["user_id"] == mock_user.id
            assert pred["status"] == "pending"
            assert pred["data"] == {"text": "Тестовый текст"}
            assert pred["model_version"] == "v1.0"
        mock_service.get_user_predictions.assert_called_once_with(mock_user.id)


# Тесты для безопасности API
class TestAPISecurity:
    """Тесты для проверки безопасности API."""
    
    def test_protected_endpoints_without_token(self, client):
        """Тест защищенных эндпоинтов без токена авторизации."""
        # Список защищенных эндпоинтов
        protected_endpoints = [
            "/users/me",
            "/transactions/balance",
            "/transactions/history",
            "/predictions/",
            "/predictions/my"
        ]
        
        # Проверка каждого эндпоинта
        for endpoint in protected_endpoints:
            # Определяем метод
            method = client.post if endpoint == "/predictions/" else client.get
            
            # Данные для POST-запросов
            data = {"data": {"text": "test"}, "model_version": "v1.0"} if endpoint == "/predictions/" else None
            
            # Отправка запроса
            if data:
                response = method(endpoint, json=data)
            else:
                response = method(endpoint)
            
            # Проверки
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Not authenticated" in response.json()["detail"]
    
    def test_token_with_invalid_signature(self, client):
        """Тест запроса с токеном с неверной подписью."""
        # Настройка моков
        headers = {"Authorization": "Bearer invalid.token.signature"}
        
        # Список защищенных эндпоинтов
        protected_endpoints = [
            "/users/me",
            "/transactions/balance"
        ]
        
        # Патч для проверки токена
        with patch("app.api.deps.verify_access_token", side_effect=ValueError("Invalid token")):
            # Проверка каждого эндпоинта
            for endpoint in protected_endpoints:
                # Отправка запроса
                response = client.get(endpoint, headers=headers)
                
                # Проверки
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Could not validate credentials" in response.json()["detail"]
    
    def test_token_with_expired_timestamp(self, client):
        """Тест запроса с истекшим токеном."""
        # Настройка моков
        headers = {"Authorization": "Bearer expired.token"}
        
        # Список защищенных эндпоинтов
        protected_endpoints = [
            "/users/me",
            "/transactions/balance"
        ]
        
        # Патч для проверки токена
        with patch("app.api.deps.verify_access_token", side_effect=ValueError("Token expired")):
            # Проверка каждого эндпоинта
            for endpoint in protected_endpoints:
                # Отправка запроса
                response = client.get(endpoint, headers=headers)
                
                # Проверки
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Could not validate credentials" in response.json()["detail"] 