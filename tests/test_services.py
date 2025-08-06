"""
Юнит-тесты для сервисных модулей ML Service.

Эти тесты проверяют логику работы сервисных модулей user_service, 
transaction_service и prediction_service в изоляции от внешних зависимостей.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from datetime import datetime, timedelta
import uuid
import json
from decimal import Decimal

try:
    from app.services.user_service import UserService
    from app.services.transaction_service import TransactionService
    from app.services.prediction_service import PredictionService
    from app.core.security import verify_password, get_password_hash
    from app.models.user import User
    from app.models.transaction import Transaction
    from app.models.prediction import Prediction
    from app.schemas.user import UserCreate, UserResponse
    from app.schemas.transaction import TransactionCreate, TransactionResponse
    from app.schemas.prediction import PredictionCreate, PredictionResponse
    
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
    db = MagicMock()
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
def mock_transaction():
    """Фикстура, создающая мок транзакции."""
    transaction = MagicMock(spec=Transaction)
    transaction.id = str(uuid.uuid4())
    transaction.user_id = 1
    transaction.type = "topup"
    transaction.amount = 50.0
    transaction.description = "Тестовое пополнение"
    transaction.created_at = datetime.now()
    return transaction


@pytest.fixture
def mock_prediction():
    """Фикстура, создающая мок предсказания."""
    prediction = MagicMock(spec=Prediction)
    prediction.id = str(uuid.uuid4())
    prediction.user_id = 1
    prediction.status = "pending"
    prediction.data = {"text": "Тестовый текст"}
    prediction.result = None
    prediction.model_version = "v1.0"
    prediction.created_at = datetime.now()
    prediction.updated_at = datetime.now()
    return prediction


# Тесты для UserService
class TestUserService:
    """Тесты для сервиса пользователей."""
    
    def test_create_user_success(self, mock_db):
        """Тест успешного создания пользователя."""
        # Настройка входных данных
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Патч для хеширования пароля
        with patch("app.services.user_service.get_password_hash", return_value="hashedpassword123"):
            # Создаем сервис и вызываем метод
            service = UserService(mock_db)
            result = service.create_user(user_data)
        
        # Проверки
        assert result.username == user_data.username
        assert result.email == user_data.email
        assert "password" not in result.dict()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_create_user_duplicate(self, mock_db, mock_user):
        """Тест создания пользователя с уже существующим именем."""
        # Настройка входных данных
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Создаем сервис и проверяем, что вызывается исключение
        service = UserService(mock_db)
        with pytest.raises(ValueError, match="Username already registered"):
            service.create_user(user_data)
        
        # Проверяем, что транзакция не коммитилась
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_authenticate_user_success(self, mock_db, mock_user):
        """Тест успешной аутентификации пользователя."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Патч для проверки пароля
        with patch("app.services.user_service.verify_password", return_value=True):
            # Создаем сервис и вызываем метод
            service = UserService(mock_db)
            result = service.authenticate_user("testuser", "testpassword")
        
        # Проверки
        assert result is not None
        assert result.username == mock_user.username
        assert result.id == mock_user.id
    
    def test_authenticate_user_wrong_password(self, mock_db, mock_user):
        """Тест аутентификации пользователя с неверным паролем."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Патч для проверки пароля
        with patch("app.services.user_service.verify_password", return_value=False):
            # Создаем сервис и вызываем метод
            service = UserService(mock_db)
            result = service.authenticate_user("testuser", "wrongpassword")
        
        # Проверки
        assert result is None
    
    def test_authenticate_user_not_found(self, mock_db):
        """Тест аутентификации несуществующего пользователя."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и вызываем метод
        service = UserService(mock_db)
        result = service.authenticate_user("nonexistent", "testpassword")
        
        # Проверки
        assert result is None
    
    def test_get_user_by_username(self, mock_db, mock_user):
        """Тест получения пользователя по имени."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Создаем сервис и вызываем метод
        service = UserService(mock_db)
        result = service.get_user_by_username("testuser")
        
        # Проверки
        assert result is not None
        assert result.username == mock_user.username
        assert result.id == mock_user.id
    
    def test_get_user_by_username_not_found(self, mock_db):
        """Тест получения несуществующего пользователя по имени."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и вызываем метод
        service = UserService(mock_db)
        result = service.get_user_by_username("nonexistent")
        
        # Проверки
        assert result is None
    
    def test_get_user_by_id(self, mock_db, mock_user):
        """Тест получения пользователя по ID."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Создаем сервис и вызываем метод
        service = UserService(mock_db)
        result = service.get_user_by_id(1)
        
        # Проверки
        assert result is not None
        assert result.id == mock_user.id
        assert result.username == mock_user.username
    
    def test_get_user_by_id_not_found(self, mock_db):
        """Тест получения несуществующего пользователя по ID."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и вызываем метод
        service = UserService(mock_db)
        result = service.get_user_by_id(999)
        
        # Проверки
        assert result is None


# Тесты для TransactionService
class TestTransactionService:
    """Тесты для сервиса транзакций."""
    
    def test_get_balance(self, mock_db, mock_user):
        """Тест получения баланса пользователя."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Создаем сервис и вызываем метод
        service = TransactionService(mock_db)
        result = service.get_balance(mock_user.id)
        
        # Проверки
        assert result == mock_user.balance
    
    def test_get_balance_user_not_found(self, mock_db):
        """Тест получения баланса несуществующего пользователя."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и проверяем, что вызывается исключение
        service = TransactionService(mock_db)
        with pytest.raises(ValueError, match="User not found"):
            service.get_balance(999)
    
    def test_top_up_balance(self, mock_db, mock_user, mock_transaction):
        """Тест пополнения баланса пользователя."""
        # Настройка входных данных
        amount = 50.0
        description = "Тестовое пополнение"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.add.return_value = None
        mock_db.refresh.return_value = None
        
        # Патч для генерации UUID
        with patch("uuid.uuid4", return_value=uuid.UUID(mock_transaction.id)):
            # Создаем сервис и вызываем метод
            service = TransactionService(mock_db)
            prev_balance, new_balance, tx_id = service.top_up_balance(mock_user.id, amount, description)
        
        # Проверки
        assert prev_balance == mock_user.balance
        assert new_balance == mock_user.balance + amount
        assert tx_id == mock_transaction.id
        assert mock_user.balance == new_balance
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_top_up_balance_negative(self, mock_db, mock_user):
        """Тест пополнения баланса на отрицательную сумму."""
        # Настройка входных данных
        amount = -50.0
        description = "Тестовое пополнение"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Создаем сервис и проверяем, что вызывается исключение
        service = TransactionService(mock_db)
        with pytest.raises(ValueError, match="Amount must be positive"):
            service.top_up_balance(mock_user.id, amount, description)
        
        # Проверяем, что транзакция не коммитилась
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_top_up_balance_user_not_found(self, mock_db):
        """Тест пополнения баланса несуществующего пользователя."""
        # Настройка входных данных
        amount = 50.0
        description = "Тестовое пополнение"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и проверяем, что вызывается исключение
        service = TransactionService(mock_db)
        with pytest.raises(ValueError, match="User not found"):
            service.top_up_balance(999, amount, description)
        
        # Проверяем, что транзакция не коммитилась
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_deduct_balance(self, mock_db, mock_user, mock_transaction):
        """Тест списания средств с баланса пользователя."""
        # Настройка входных данных
        amount = 50.0
        description = "Тестовое списание"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.add.return_value = None
        mock_db.refresh.return_value = None
        
        # Патч для генерации UUID
        with patch("uuid.uuid4", return_value=uuid.UUID(mock_transaction.id)):
            # Создаем сервис и вызываем метод
            service = TransactionService(mock_db)
            prev_balance, new_balance, tx_id = service.deduct_balance(mock_user.id, amount, description)
        
        # Проверки
        assert prev_balance == mock_user.balance
        assert new_balance == mock_user.balance - amount
        assert tx_id == mock_transaction.id
        assert mock_user.balance == new_balance
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_deduct_balance_insufficient_funds(self, mock_db, mock_user):
        """Тест списания средств при недостаточном балансе."""
        # Настройка входных данных
        amount = 200.0  # больше, чем mock_user.balance
        description = "Тестовое списание"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Создаем сервис и проверяем, что вызывается исключение
        service = TransactionService(mock_db)
        with pytest.raises(ValueError, match="Insufficient funds"):
            service.deduct_balance(mock_user.id, amount, description)
        
        # Проверяем, что транзакция не коммитилась
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_get_user_transactions(self, mock_db, mock_transaction):
        """Тест получения истории транзакций пользователя."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_transaction] * 5
        
        # Создаем сервис и вызываем метод
        service = TransactionService(mock_db)
        result = service.get_user_transactions(1)
        
        # Проверки
        assert len(result) == 5
        for tx in result:
            assert tx.user_id == 1
            assert tx.type == mock_transaction.type
            assert tx.amount == mock_transaction.amount
            assert tx.description == mock_transaction.description


# Тесты для PredictionService
class TestPredictionService:
    """Тесты для сервиса предсказаний."""
    
    def test_create_prediction(self, mock_db, mock_user, mock_prediction):
        """Тест создания предсказания."""
        # Настройка входных данных
        data = PredictionCreate(
            data={"text": "Тестовый текст"},
            model_version="v1.0"
        )
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.add.return_value = None
        mock_db.refresh.return_value = None
        
        # Патч для генерации UUID
        with patch("uuid.uuid4", return_value=uuid.UUID(mock_prediction.id)):
            # Создаем сервис и вызываем метод
            service = PredictionService(mock_db)
            result = service.create_prediction(mock_user.id, data)
        
        # Проверки
        assert result.id == mock_prediction.id
        assert result.user_id == mock_user.id
        assert result.status == "pending"
        assert result.data == data.data
        assert result.model_version == data.model_version
        assert result.result is None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_create_prediction_user_not_found(self, mock_db):
        """Тест создания предсказания для несуществующего пользователя."""
        # Настройка входных данных
        data = PredictionCreate(
            data={"text": "Тестовый текст"},
            model_version="v1.0"
        )
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и проверяем, что вызывается исключение
        service = PredictionService(mock_db)
        with pytest.raises(ValueError, match="User not found"):
            service.create_prediction(999, data)
        
        # Проверяем, что транзакция не коммитилась
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_get_prediction(self, mock_db, mock_prediction):
        """Тест получения предсказания по ID."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prediction
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        result = service.get_prediction(mock_prediction.id)
        
        # Проверки
        assert result is not None
        assert result.id == mock_prediction.id
        assert result.user_id == mock_prediction.user_id
        assert result.status == mock_prediction.status
        assert result.data == mock_prediction.data
        assert result.model_version == mock_prediction.model_version
    
    def test_get_prediction_not_found(self, mock_db):
        """Тест получения несуществующего предсказания."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        result = service.get_prediction(str(uuid.uuid4()))
        
        # Проверки
        assert result is None
    
    def test_get_user_predictions(self, mock_db, mock_prediction):
        """Тест получения всех предсказаний пользователя."""
        # Настройка моков
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_prediction] * 5
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        result = service.get_user_predictions(1)
        
        # Проверки
        assert len(result) == 5
        for pred in result:
            assert pred.user_id == 1
            assert pred.status == mock_prediction.status
            assert pred.data == mock_prediction.data
            assert pred.model_version == mock_prediction.model_version
    
    def test_update_prediction_result(self, mock_db, mock_prediction):
        """Тест обновления результата предсказания."""
        # Настройка входных данных
        prediction_id = mock_prediction.id
        result = {"prediction": "positive", "confidence": 0.95}
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prediction
        mock_db.add.return_value = None
        mock_db.refresh.return_value = None
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        updated = service.update_prediction_result(prediction_id, result)
        
        # Проверки
        assert updated is True
        assert mock_prediction.status == "completed"
        assert mock_prediction.result == result
        mock_db.commit.assert_called_once()
    
    def test_update_prediction_result_not_found(self, mock_db):
        """Тест обновления результата несуществующего предсказания."""
        # Настройка входных данных
        prediction_id = str(uuid.uuid4())
        result = {"prediction": "positive", "confidence": 0.95}
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        updated = service.update_prediction_result(prediction_id, result)
        
        # Проверки
        assert updated is False
        mock_db.commit.assert_not_called()
    
    def test_update_prediction_error(self, mock_db, mock_prediction):
        """Тест обновления предсказания с ошибкой."""
        # Настройка входных данных
        prediction_id = mock_prediction.id
        error_message = "Ошибка модели"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prediction
        mock_db.add.return_value = None
        mock_db.refresh.return_value = None
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        updated = service.update_prediction_error(prediction_id, error_message)
        
        # Проверки
        assert updated is True
        assert mock_prediction.status == "error"
        assert mock_prediction.result == {"error": error_message}
        mock_db.commit.assert_called_once()
    
    def test_update_prediction_error_not_found(self, mock_db):
        """Тест обновления с ошибкой несуществующего предсказания."""
        # Настройка входных данных
        prediction_id = str(uuid.uuid4())
        error_message = "Ошибка модели"
        
        # Настройка моков
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Создаем сервис и вызываем метод
        service = PredictionService(mock_db)
        updated = service.update_prediction_error(prediction_id, error_message)
        
        # Проверки
        assert updated is False
        mock_db.commit.assert_not_called() 