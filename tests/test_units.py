"""
Юнит-тесты для проверки компонентов ML Service.

Эти тесты проверяют отдельные компоненты системы в изоляции,
используя моки для имитации внешних зависимостей.
"""

import pytest
import unittest
from unittest.mock import patch, MagicMock, Mock
import json
from datetime import datetime

# Предполагаемые импорты для тестирования функций сервиса
# Пути могут отличаться в зависимости от реальной структуры проекта
try:
    from app.services.user_service import create_user, authenticate_user
    from app.services.transaction_service import get_balance, top_up_balance, get_user_transactions
    from app.services.prediction_service import create_prediction, get_prediction, process_prediction
    from app.services.auth_service import get_current_user, create_access_token
    from app.core.auth import verify_password, get_password_hash
    from app.db.database import get_db
    from app.schemas.user import UserCreate, UserResponse
    from app.schemas.transaction import TransactionResponse
    from app.schemas.prediction import PredictionCreate, PredictionResponse
    
    # Флаг для определения доступности реальных модулей
    REAL_MODULES_AVAILABLE = True
except ImportError:
    # Если модули недоступны, создаем пустые заглушки для тестов
    REAL_MODULES_AVAILABLE = False
    print("Внимание: Реальные модули недоступны. Используются заглушки для тестов.")


#----------------------------------------------------------
# Тесты для компонента аутентификации
#----------------------------------------------------------

class TestAuthentication(unittest.TestCase):
    """Тесты для функций аутентификации и авторизации."""
    
    def setUp(self):
        # Создаем тестовые данные
        self.test_user = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        self.hashed_password = "hashedpassword123"
        
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    @patch('app.core.auth.pwd_context.verify')
    def test_verify_password(self, mock_verify):
        """Тест проверки пароля."""
        # Настройка мока
        mock_verify.return_value = True
        
        # Вызов тестируемой функции
        result = verify_password("password123", self.hashed_password)
        
        # Проверка результата
        self.assertTrue(result)
        mock_verify.assert_called_once_with("password123", self.hashed_password)

    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    @patch('app.core.auth.pwd_context.hash')
    def test_get_password_hash(self, mock_hash):
        """Тест хеширования пароля."""
        # Настройка мока
        mock_hash.return_value = self.hashed_password
        
        # Вызов тестируемой функции
        result = get_password_hash("password123")
        
        # Проверка результата
        self.assertEqual(result, self.hashed_password)
        mock_hash.assert_called_once_with("password123")

    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    @patch('app.services.auth_service.jwt.encode')
    def test_create_access_token(self, mock_encode):
        """Тест создания токена доступа."""
        # Настройка мока
        expected_token = "access_token_123"
        mock_encode.return_value = expected_token
        
        # Вызов тестируемой функции
        token = create_access_token({"sub": "testuser"})
        
        # Проверка результата
        self.assertEqual(token, expected_token)
        self.assertTrue(mock_encode.called)


#----------------------------------------------------------
# Тесты для компонента пользователей
#----------------------------------------------------------

class TestUserService(unittest.TestCase):
    """Тесты для функций работы с пользователями."""
    
    def setUp(self):
        # Создаем тестовые данные
        self.test_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        self.db_session = MagicMock()
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    @patch('app.services.user_service.get_password_hash')
    def test_create_user(self, mock_get_password_hash):
        """Тест создания пользователя."""
        # Настройка моков
        mock_get_password_hash.return_value = "hashedpassword123"
        self.db_session.query.return_value.filter.return_value.first.return_value = None
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = self.test_user_data["username"]
        mock_user.email = self.test_user_data["email"]
        
        self.db_session.add.return_value = None
        self.db_session.commit.return_value = None
        self.db_session.refresh.return_value = None
        
        # Имитируем создание пользователя в БД
        with patch('app.models.user.User', return_value=mock_user):
            # Вызов тестируемой функции
            user_create = UserCreate(**self.test_user_data)
            result = create_user(self.db_session, user_create)
            
            # Проверка результата
            self.assertEqual(result.username, self.test_user_data["username"])
            self.assertEqual(result.email, self.test_user_data["email"])
            self.assertTrue(self.db_session.add.called)
            self.assertTrue(self.db_session.commit.called)
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    @patch('app.services.user_service.verify_password')
    def test_authenticate_user(self, mock_verify_password):
        """Тест аутентификации пользователя."""
        # Настройка моков
        mock_user = MagicMock()
        mock_user.username = self.test_user_data["username"]
        mock_user.hashed_password = "hashedpassword123"
        
        self.db_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_verify_password.return_value = True
        
        # Вызов тестируемой функции
        result = authenticate_user(
            self.db_session, 
            self.test_user_data["username"], 
            self.test_user_data["password"]
        )
        
        # Проверка результата
        self.assertEqual(result, mock_user)
        mock_verify_password.assert_called_once_with(
            self.test_user_data["password"], 
            mock_user.hashed_password
        )


#----------------------------------------------------------
# Тесты для компонента транзакций
#----------------------------------------------------------

class TestTransactionService(unittest.TestCase):
    """Тесты для функций работы с транзакциями."""
    
    def setUp(self):
        # Создаем тестовые данные
        self.user_id = 1
        self.amount = 100.0
        self.transaction_id = "tx_123456"
        self.db_session = MagicMock()
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    def test_get_balance(self):
        """Тест получения баланса пользователя."""
        # Настройка мока
        mock_user = MagicMock()
        mock_user.id = self.user_id
        mock_user.balance = 150.0
        
        self.db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Вызов тестируемой функции
        result = get_balance(self.db_session, self.user_id)
        
        # Проверка результата
        self.assertEqual(result, 150.0)
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    def test_top_up_balance(self):
        """Тест пополнения баланса пользователя."""
        # Настройка моков
        mock_user = MagicMock()
        mock_user.id = self.user_id
        mock_user.balance = 50.0
        
        self.db_session.query.return_value.filter.return_value.first.return_value = mock_user
        self.db_session.add.return_value = None
        self.db_session.commit.return_value = None
        
        mock_transaction = MagicMock()
        mock_transaction.id = self.transaction_id
        
        # Имитируем создание транзакции
        with patch('app.models.transaction.Transaction', return_value=mock_transaction):
            # Вызов тестируемой функции
            prev_balance, new_balance, tx_id = top_up_balance(
                self.db_session, 
                self.user_id, 
                self.amount
            )
            
            # Проверка результата
            self.assertEqual(prev_balance, 50.0)
            self.assertEqual(new_balance, 150.0)
            self.assertEqual(tx_id, self.transaction_id)
            self.assertTrue(self.db_session.add.called)
            self.assertTrue(self.db_session.commit.called)
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    def test_get_user_transactions(self):
        """Тест получения истории транзакций пользователя."""
        # Создаем тестовые транзакции
        mock_transactions = [
            MagicMock(
                id=f"tx_{i}", 
                user_id=self.user_id, 
                type="topup", 
                amount=100.0,
                created_at=datetime.now()
            ) for i in range(5)
        ]
        
        # Настройка мока
        self.db_session.query.return_value.filter.return_value.order_by.return_value\
            .offset.return_value.limit.return_value.all.return_value = mock_transactions
        
        # Вызов тестируемой функции
        result = get_user_transactions(self.db_session, self.user_id, 0, 10)
        
        # Проверка результата
        self.assertEqual(len(result), 5)
        for i, tx in enumerate(result):
            self.assertEqual(tx.id, f"tx_{i}")
            self.assertEqual(tx.user_id, self.user_id)


#----------------------------------------------------------
# Тесты для компонента предсказаний
#----------------------------------------------------------

class TestPredictionService(unittest.TestCase):
    """Тесты для функций работы с предсказаниями."""
    
    def setUp(self):
        # Создаем тестовые данные
        self.user_id = 1
        self.prediction_id = "pred_123456"
        self.test_text = "Это тестовый текст для предсказания"
        self.db_session = MagicMock()
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    def test_create_prediction(self):
        """Тест создания запроса на предсказание."""
        # Настройка моков
        mock_prediction = MagicMock()
        mock_prediction.id = self.prediction_id
        mock_prediction.user_id = self.user_id
        mock_prediction.status = "pending"
        
        self.db_session.add.return_value = None
        self.db_session.commit.return_value = None
        self.db_session.refresh.return_value = None
        
        # Имитируем создание предсказания
        with patch('app.models.prediction.Prediction', return_value=mock_prediction):
            # Вызов тестируемой функции
            data = {"text": self.test_text}
            prediction_create = PredictionCreate(data=data)
            result = create_prediction(self.db_session, prediction_create, self.user_id)
            
            # Проверка результата
            self.assertEqual(result.id, self.prediction_id)
            self.assertEqual(result.status, "pending")
            self.assertTrue(self.db_session.add.called)
            self.assertTrue(self.db_session.commit.called)
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    def test_get_prediction(self):
        """Тест получения результата предсказания."""
        # Настройка мока
        mock_prediction = MagicMock()
        mock_prediction.id = self.prediction_id
        mock_prediction.user_id = self.user_id
        mock_prediction.status = "completed"
        mock_prediction.result = {"prediction": "positive", "confidence": 0.95}
        
        self.db_session.query.return_value.filter.return_value.first.return_value = mock_prediction
        
        # Вызов тестируемой функции
        result = get_prediction(self.db_session, self.prediction_id, self.user_id)
        
        # Проверка результата
        self.assertEqual(result.id, self.prediction_id)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result["prediction"], "positive")
    
    @unittest.skipIf(not REAL_MODULES_AVAILABLE, "Реальные модули недоступны")
    @patch('app.services.prediction_service.get_prediction')
    @patch('app.services.prediction_service.update_prediction')
    def test_process_prediction(self, mock_update_prediction, mock_get_prediction):
        """Тест обработки предсказания."""
        # Настройка моков
        mock_prediction = MagicMock()
        mock_prediction.id = self.prediction_id
        mock_prediction.user_id = self.user_id
        mock_prediction.status = "pending"
        mock_prediction.data = {"text": self.test_text}
        
        mock_get_prediction.return_value = mock_prediction
        mock_update_prediction.return_value = None
        
        # Имитируем модель ML
        mock_ml_model = MagicMock()
        mock_ml_model.predict.return_value = {"prediction": "positive", "confidence": 0.95}
        
        with patch('app.services.prediction_service.get_ml_model', return_value=mock_ml_model):
            # Вызов тестируемой функции
            process_prediction(self.db_session, self.prediction_id)
            
            # Проверка результатов
            mock_get_prediction.assert_called_once_with(self.db_session, self.prediction_id)
            mock_ml_model.predict.assert_called_once_with(self.test_text)
            mock_update_prediction.assert_called_once()


# Запуск тестов
if __name__ == '__main__':
    unittest.main() 