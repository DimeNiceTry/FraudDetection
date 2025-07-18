"""
Скрипт для создания тестового пользователя с незашифрованным паролем.
"""
from sqlalchemy.orm import Session
from app.db.session import engine
from ml_service.models.user import User
from ml_service.models.balance import Balance

def create_test_user():
    session = Session(engine)
    try:
        user = User(
            username='testuser11',
            email='testuser11@example.com',
            password='password123'  # Пароль в открытом виде
        )
        session.add(user)
        session.flush()
        
        # Создаем баланс для пользователя
        balance = Balance(user_id=user.id, amount=10.0)
        session.add(balance)
        
        session.commit()
        print('Тестовый пользователь создан успешно')
    except Exception as e:
        session.rollback()
        print(f'Ошибка при создании пользователя: {e}')
    finally:
        session.close()

if __name__ == '__main__':
    create_test_user() 