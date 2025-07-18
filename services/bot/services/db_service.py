"""
Сервис для работы с базой данных.
"""
import os
import logging
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Enum, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# SQLAlchemy настройки
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Модели SQLAlchemy
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String)
    password = Column(String)
    
    balances = relationship("Balance", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class Balance(Base):
    __tablename__ = 'balances'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="balances")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # deposit, withdrawal, payment
    status = Column(String, nullable=False)  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="transactions")

def get_db_connection():
    """
    Создает соединение с базой данных.
    
    Returns:
        psycopg2.connection: Соединение с базой данных
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise

def wait_for_db():
    """
    Ожидает доступности базы данных.
    
    Returns:
        bool: True если подключение успешно, False в случае ошибки
    """
    retry_count = 0
    max_retries = 30
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к PostgreSQL (попытка {retry_count + 1}/{max_retries})...")
            conn = get_db_connection()
            logger.info("Подключение к PostgreSQL успешно установлено")
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False

async def register_user(telegram_id, username):
    """
    Регистрирует пользователя в системе.
    
    Args:
        telegram_id: ID пользователя в Telegram
        username: Имя пользователя в Telegram
        
    Returns:
        int: ID пользователя в базе данных
    """
    conn = None
    try:
        logger.info(f"Пытаемся зарегистрировать пользователя: tg_{telegram_id}")
        
        # Проверяем доступность базы данных
        try:
            conn = get_db_connection()
            logger.info("Соединение с базой данных установлено")
        except Exception as db_error:
            logger.error(f"Ошибка подключения к базе данных: {db_error}")
            raise
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем, существует ли пользователь
        logger.info(f"Проверяем существование пользователя: tg_{telegram_id}")
        cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{telegram_id}",))
        user = cursor.fetchone()
        
        if not user:
            # Создаем нового пользователя
            logger.info(f"Пользователь не найден, создаем нового: tg_{telegram_id}")
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                (f"tg_{telegram_id}", f"{username}@telegram.org", f"tg_pass_{telegram_id}")
            )
            user_id = cursor.fetchone()["id"]
            
            # Создаем баланс для пользователя
            logger.info(f"Создаем баланс для нового пользователя: {user_id}")
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
                (user_id, 10.0)  # Даем 10 кредитов новому пользователю
            )
            
            conn.commit()
            logger.info(f"Зарегистрирован новый пользователь: {username} (ID: {telegram_id}, DB_ID: {user_id})")
            return user_id
        else:
            user_id = user["id"]
            logger.info(f"Пользователь уже существует: {username} (ID: {telegram_id}, DB_ID: {user_id})")
            return user_id
    
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        if conn:
            conn.rollback()
        raise
    
    finally:
        if conn:
            conn.close()
            logger.info("Соединение с базой данных закрыто")

async def get_user_balance(user_id):
    """
    Получает баланс пользователя через SQLAlchemy ORM.
    
    Args:
        user_id: ID пользователя в базе данных
        
    Returns:
        float: Баланс пользователя
    """
    session = None
    try:
        # Создаем сессию SQLAlchemy
        session = Session()
        
        # Получаем баланс пользователя
        balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            return 0.0
        
        return float(balance.amount)
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        raise
    
    finally:
        if session:
            session.close()

async def get_db_user_id(telegram_id):
    """
    Получает внутренний ID пользователя в базе данных по Telegram ID.
    
    Args:
        telegram_id: ID пользователя в Telegram
        
    Returns:
        int: ID пользователя в базе данных или None, если не найден
    """
    session = None
    try:
        logger.info(f"Получение внутреннего ID пользователя для Telegram ID: {telegram_id}")
        
        # Создаем сессию SQLAlchemy
        session = Session()
        
        # Получаем пользователя по username (который содержит Telegram ID)
        user = session.query(User).filter(User.username == f"tg_{telegram_id}").first()
        
        if not user:
            logger.warning(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            return None
        
        logger.info(f"Найден внутренний ID пользователя: {user.id} для Telegram ID: {telegram_id}")
        return user.id
    
    except Exception as e:
        logger.error(f"Ошибка при получении внутреннего ID пользователя: {e}")
        return None
    
    finally:
        if session:
            session.close()

async def add_user_balance(user_id, amount):
    """
    Пополняет баланс пользователя через SQLAlchemy ORM.
    
    Args:
        user_id: ID пользователя в базе данных
        amount: Сумма пополнения
        
    Returns:
        float: Новый баланс пользователя
    """
    session = None
    try:
        logger.info(f"Пополнение баланса для пользователя {user_id} на {amount} кредитов")
        
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")
        
        # Создаем сессию SQLAlchemy
        session = Session()
        
        # Получаем баланс пользователя
        balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            # Создаем новый баланс
            logger.info(f"Баланс для пользователя {user_id} не найден, создаем новый")
            balance = Balance(user_id=user_id, amount=amount)
            session.add(balance)
            new_balance = amount
        else:
            # Обновляем существующий баланс
            new_balance = balance.amount + amount
            balance.amount = new_balance
        
        # Создаем запись о транзакции
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type="deposit",
            status="completed"
        )
        session.add(transaction)
        
        # Сохраняем изменения в базе данных
        session.commit()
        logger.info(f"Баланс пользователя {user_id} успешно пополнен. Новый баланс: {new_balance}")
        
        return new_balance
    
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса: {e}")
        if session:
            session.rollback()
        raise
    
    finally:
        if session:
            session.close()
            logger.info("Сессия SQLAlchemy закрыта") 