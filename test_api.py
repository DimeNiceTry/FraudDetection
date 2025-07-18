"""
Юнит-тесты для API эндпоинтов ML Service.

Эти тесты проверяют работу API эндпоинтов в изоляции,
используя FastAPI TestClient и моки для внешних зависимостей.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime
import json
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

try:
    from app.main import app
    from app.api.deps import get_db, get_current_user
    from app.schemas.user import UserCreate, UserResponse
    from app.schemas.token import Token
    from app.schemas.transaction import TransactionCreate, TransactionResponse
    from app.schemas.prediction import PredictionCreate, PredictionResponse
    from app.models.user import User
    from app.models.transaction import Transaction
    from app.models.prediction import Prediction
    
    # Флаг для определения доступности реальных модулей
    REAL_MODULES_AVAILABLE = True
except ImportError:
    REAL_MODULES_AVAILABLE = False
    print("Внимание: Реальные модули недоступны. Используются заглушки для тестов.")
    app = FastAPI()


# Пропускаем тесты, если модули недоступны
pytestmark = pytest.mark.skipif(not REAL_MODULES_AVAILABLE, reason="Реальные модули недоступны")


# Фикстуры для тестов
@pytest.fixture
def test_db():
    """Фикстура, создающая мок сессии БД."""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def test_user():
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
def test_token():
    """Фикстура, создающая тестовый токен."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTcwMDAwMDAwMH0.test"


@pytest.fixture
def client(test_db, test_user):
    """Фикстура, создающая тестовый клиент FastAPI."""
    # Переопределяем зависимости для тестов
    async def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    async def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    client = TestClient(app)
    yield client
    
    # Очистка переопределенных зависимостей
    app.dependency_overrides = {}


@pytest.fixture
def authenticated_client(client, test_token):
    """Фикстура, создающая аутентифицированный тестовый клиент."""
    client.headers = {"Authorization": f"Bearer {test_token}"}
    return client


# Тесты для системных эндпоинтов
class TestSystemEndpoints:
    """Тесты для системных эндпоинтов API."""
    
    def test_health_endpoint(self, client):
        """Тест эндпоинта проверки здоровья системы."""
        # Вызов тестируемого эндпоинта
        response = client.get("/health")
        
        # Проверки
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# Тесты для эндпоинтов пользователей
class TestUserEndpoints:
    """Тесты для эндпоинтов пользователей API."""
    
    def test_create_user_success(self, client, test_db, test_user):
        """Тест успешного создания пользователя."""
        # Настройка входных данных
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123"
        }
        
        # Настройка мока
        test_db.query.return_value.filter.return_value.first.return_value = None
        
        # Настройка патчей
        with patch('app.services.user_service.create_user', return_value=test_user):
            # Вызов тестируемого эндпоинта
            response = client.post("/users/", json=user_data)
            
            # Проверки
            assert response.status_code == 201
            assert "id" in response.json()
            assert "username" in response.json()
            assert "email" in response.json()
            assert "password" not in response.json()
    
    def test_create_user_duplicate_username(self, client, test_db, test_user):
        """Тест создания пользователя с уже существующим именем."""
        # Настройка входных данных
        user_data = {
            "username": "testuser",
            "email": "new@example.com",
            "password": "password123"
        }
        
        # Настройка патчей
        with patch('app.services.user_service.create_user', side_effect=ValueError("Username already registered")):
            # Вызов тестируемого эндпоинта
            response = client.post("/users/", json=user_data)
            
            # Проверки
            assert response.status_code == 400
            assert "detail" in response.json()
            assert "Username already registered" in response.json()["detail"]
    
    def test_login_success(self, client, test_db, test_user, test_token):
        """Тест успешного входа в систему."""
        # Настройка входных данных
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        
        # Настройка мока
        test_db.query.return_value.filter.return_value.first.return_value = test_user
        
        # Настройка патчей
        with patch('app.api.endpoints.users.authenticate_user', return_value=test_user):
            with patch('app.api.endpoints.users.create_access_token', return_value=test_token):
                # Вызов тестируемого эндпоинта
                response = client.post("/users/login", data=login_data)
                
                # Проверки
                assert response.status_code == 200
                assert response.json()["access_token"] == test_token
                assert response.json()["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, test_db):
        """Тест входа в систему с неверными учетными данными."""
        # Настройка входных данных
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        
        # Настройка патчей
        with patch('app.api.endpoints.users.authenticate_user', return_value=None):
            # Вызов тестируемого эндпоинта
            response = client.post("/users/login", data=login_data)
            
            # Проверки
            assert response.status_code == 401
            assert "detail" in response.json()
            assert "Incorrect username or password" in response.json()["detail"]
    
    def test_get_current_user(self, authenticated_client, test_user):
        """Тест получения текущего пользователя."""
        # Вызов тестируемого эндпоинта
        response = authenticated_client.get("/users/me")
        
        # Проверки
        assert response.status_code == 200
        assert response.json()["username"] == test_user.username
        assert response.json()["email"] == test_user.email
        assert "password" not in response.json()


# Тесты для эндпоинтов транзакций
class TestTransactionEndpoints:
    """Тесты для эндпоинтов транзакций API."""
    
    def test_get_balance_success(self, authenticated_client, test_db, test_user):
        """Тест успешного получения баланса."""
        # Настройка патчей
        with patch('app.services.transaction_service.get_balance', return_value=test_user.balance):
            # Вызов тестируемого эндпоинта
            response = authenticated_client.get("/transactions/balance")
            
            # Проверки
            assert response.status_code == 200
            assert response.json()["balance"] == test_user.balance
    
    def test_top_up_balance_success(self, authenticated_client, test_db, test_user):
        """Тест успешного пополнения баланса."""
        # Настройка входных данных
        topup_data = {
            "amount": 50.0,
            "description": "Тестовое пополнение"
        }
        
        # Настройка патчей
        with patch('app.services.transaction_service.top_up_balance', return_value=(100.0, 150.0, "tx_123")):
            # Вызов тестируемого эндпоинта
            response = authenticated_client.post("/transactions/topup", json=topup_data)
            
            # Проверки
            assert response.status_code == 200
            assert response.json()["previous_balance"] == 100.0
            assert response.json()["current_balance"] == 150.0
            assert response.json()["transaction_id"] == "tx_123"
    
    def test_get_transactions_success(self, authenticated_client, test_db, test_user):
        """Тест успешного получения транзакций."""
        # Создаем список транзакций
        mock_transaction = MagicMock(spec=Transaction)
        mock_transaction.id = "tx_123"
        mock_transaction.user_id = test_user.id
        mock_transaction.type = "topup"
        mock_transaction.amount = 50.0
        mock_transaction.description = "Тестовое пополнение"
        mock_transaction.created_at = datetime.now()
        
        transactions = [mock_transaction] * 5
        
        # Настройка патчей
        with patch('app.services.transaction_service.get_user_transactions', return_value=transactions):
            # Вызов тестируемого эндпоинта
            response = authenticated_client.get("/transactions/history")
            
            # Проверки
            assert response.status_code == 200
            assert isinstance(response.json(), list)
            assert len(response.json()) == 5
            for tx in response.json():
                assert "id" in tx
                assert "user_id" in tx
                assert "type" in tx
                assert "amount" in tx
                assert "description" in tx
                assert "created_at" in tx


# Тесты для эндпоинтов предсказаний
class TestPredictionEndpoints:
    """Тесты для эндпоинтов предсказаний API."""
    
    def test_create_prediction_success(self, authenticated_client, test_db, test_user):
        """Тест успешного создания предсказания."""
        # Настройка входных данных
        prediction_data = {
            "data": {"text": "Тестовый текст"},
            "model_version": "v1.0"
        }
        
        # Создаем мок предсказания
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.user_id = test_user.id
        mock_prediction.status = "pending"
        mock_prediction.data = prediction_data["data"]
        mock_prediction.result = None
        mock_prediction.model_version = prediction_data["model_version"]
        mock_prediction.created_at = datetime.now()
        mock_prediction.updated_at = datetime.now()
        
        # Настройка патчей
        with patch('app.services.prediction_service.create_prediction', return_value=mock_prediction):
            with patch('app.api.endpoints.predictions.process_prediction_task', return_value=None):
                # Вызов тестируемого эндпоинта
                response = authenticated_client.post("/predictions/", json=prediction_data)
                
                # Проверки
                assert response.status_code == 202
                assert response.json()["id"] == mock_prediction.id
                assert response.json()["status"] == "pending"
                assert response.json()["data"] == prediction_data["data"]
    
    def test_get_prediction_success(self, authenticated_client, test_db, test_user):
        """Тест успешного получения предсказания."""
        # Создаем мок предсказания
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.user_id = test_user.id
        mock_prediction.status = "completed"
        mock_prediction.data = {"text": "Тестовый текст"}
        mock_prediction.result = {"prediction": "positive", "confidence": 0.95}
        mock_prediction.model_version = "v1.0"
        mock_prediction.created_at = datetime.now()
        mock_prediction.updated_at = datetime.now()
        
        # Настройка патчей
        with patch('app.services.prediction_service.get_prediction', return_value=mock_prediction):
            # Вызов тестируемого эндпоинта
            response = authenticated_client.get("/predictions/pred_123")
            
            # Проверки
            assert response.status_code == 200
            assert response.json()["id"] == mock_prediction.id
            assert response.json()["status"] == "completed"
            assert response.json()["data"] == mock_prediction.data
            assert response.json()["result"] == mock_prediction.result
    
    def test_get_prediction_not_found(self, authenticated_client, test_db):
        """Тест получения несуществующего предсказания."""
        # Настройка патчей
        with patch('app.services.prediction_service.get_prediction', return_value=None):
            # Вызов тестируемого эндпоинта
            response = authenticated_client.get("/predictions/nonexistent")
            
            # Проверки
            assert response.status_code == 404
            assert "detail" in response.json()
            assert "Prediction not found" in response.json()["detail"]
    
    def test_get_predictions_success(self, authenticated_client, test_db, test_user):
        """Тест успешного получения предсказаний пользователя."""
        # Создаем мок предсказания
        mock_prediction = MagicMock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.user_id = test_user.id
        mock_prediction.status = "completed"
        mock_prediction.data = {"text": "Тестовый текст"}
        mock_prediction.result = {"prediction": "positive", "confidence": 0.95}
        mock_prediction.model_version = "v1.0"
        mock_prediction.created_at = datetime.now()
        mock_prediction.updated_at = datetime.now()
        
        predictions = [mock_prediction] * 5
        
        # Настройка патчей
        with patch('app.services.prediction_service.get_user_predictions', return_value=predictions):
            # Вызов тестируемого эндпоинта
            response = authenticated_client.get("/predictions/history")
            
            # Проверки
            assert response.status_code == 200
            assert isinstance(response.json(), list)
            assert len(response.json()) == 5
            for pred in response.json():
                assert "id" in pred
                assert "user_id" in pred
                assert "status" in pred
                assert "data" in pred
                assert "result" in pred
                assert "model_version" in pred
                assert "created_at" in pred 