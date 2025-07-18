"""
Тестирование работы базы данных и ORM.
"""
import sys
import os
from pprint import pprint

# Добавление корневой директории проекта в sys.path 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml_service.db_config import SessionLocal
from ml_service.models.users.user_manager import UserManager
from ml_service.models.transactions.transaction_manager import TransactionManager
from ml_service.models.users.roles import AdminRole
from ml_service.models.transactions.transaction_types import TransactionType


def test_user_operations():
    """Тестирование операций с пользователями."""
    db = SessionLocal()
    try:
        user_manager = UserManager(db)
        
        print("=== Получение списка всех пользователей ===")
        users = user_manager.get_all_users()
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Role: {user.role_name}")
        
        print("\n=== Получение пользователя по имени ===")
        user = user_manager.get_user_by_username("demouser")
        if user:
            print(f"Найден пользователь: {user.username}, Email: {user.email}")
            
            print(f"\n=== Проверка аутентификации пользователя ===")
            auth_user = user_manager.authenticate_user("demouser", "demo123")
            if auth_user:
                print(f"Аутентификация успешна. Последний вход: {auth_user.last_login}")
            else:
                print("Ошибка аутентификации")
                
            print(f"\n=== Обновление данных пользователя ===")
            updated_user = user_manager.update_user(user.id, {
                "email": "updated_demo@example.com"
            })
            if updated_user:
                print(f"Email обновлен: {updated_user.email}")
                
                # Возвращаем исходный email
                user_manager.update_user(user.id, {
                    "email": "demo@example.com"
                })
        else:
            print("Пользователь не найден")
            
        # Создание временного пользователя для тестирования
        print("\n=== Создание временного тестового пользователя ===")
        try:
            test_user = user_manager.create_user(
                username="test_user",
                email="test@example.com",
                password="test123"
            )
            print(f"Создан тестовый пользователь: {test_user.username}, ID: {test_user.id}")
            
            # Удаление временного пользователя
            print("\n=== Удаление временного тестового пользователя ===")
            if user_manager.delete_user(test_user.id):
                print(f"Пользователь {test_user.username} удален")
            else:
                print("Ошибка удаления пользователя")
        except ValueError as e:
            print(f"Ошибка создания пользователя: {e}")
            
    finally:
        db.close()


def test_transaction_operations():
    """Тестирование операций с транзакциями."""
    db = SessionLocal()
    try:
        user_manager = UserManager(db)
        transaction_manager = TransactionManager(db)
        
        # Получаем демо пользователя
        user = user_manager.get_user_by_username("demouser")
        if not user:
            print("Демо пользователь не найден")
            return
            
        print(f"=== Получение баланса пользователя {user.username} ===")
        balance = transaction_manager.get_balance(user.id)
        if balance:
            print(f"Текущий баланс: {balance.amount} кредитов")
            
            # Пополнение баланса
            print("\n=== Пополнение баланса ===")
            if transaction_manager.top_up_balance(user.id, 500, "Тестовое пополнение"):
                print("Баланс успешно пополнен")
                balance = transaction_manager.get_balance(user.id)
                print(f"Новый баланс: {balance.amount} кредитов")
                
            # Списание средств
            print("\n=== Списание средств ===")
            if transaction_manager.withdraw_from_balance(user.id, 200, "Тестовое списание"):
                print("Средства успешно списаны")
                balance = transaction_manager.get_balance(user.id)
                print(f"Новый баланс: {balance.amount} кредитов")
                
            # Получение истории транзакций
            print("\n=== История всех транзакций ===")
            transactions = transaction_manager.get_transaction_history(user.id)
            for i, tx in enumerate(transactions):
                print(f"{i+1}. {tx.transaction_type.value}: {tx.amount} кредитов, {tx.created_at}")
                
            # Получение истории пополнений
            print("\n=== История пополнений ===")
            deposits = transaction_manager.get_transaction_history(
                user.id, 
                transaction_type=TransactionType.DEPOSIT
            )
            for i, tx in enumerate(deposits):
                print(f"{i+1}. {tx.transaction_type.value}: {tx.amount} кредитов, {tx.created_at}")
                
            # Получение истории списаний
            print("\n=== История списаний ===")
            withdrawals = transaction_manager.get_transaction_history(
                user.id, 
                transaction_type=TransactionType.WITHDRAWAL
            )
            for i, tx in enumerate(withdrawals):
                print(f"{i+1}. {tx.transaction_type.value}: {tx.amount} кредитов, {tx.created_at}")
        else:
            print("Баланс не найден")
    finally:
        db.close()


if __name__ == "__main__":
    print("=== ТЕСТИРОВАНИЕ ОПЕРАЦИЙ С ПОЛЬЗОВАТЕЛЯМИ ===")
    test_user_operations()
    
    print("\n\n=== ТЕСТИРОВАНИЕ ОПЕРАЦИЙ С ТРАНЗАКЦИЯМИ ===")
    test_transaction_operations() 