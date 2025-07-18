"""
Сервис для работы с моделями машинного обучения.
"""
import logging
import time
import os
import json
from datetime import datetime
from typing import Dict, Any, Union, List
import uuid
import pickle
import joblib
import numpy as np
import pandas as pd

from worker.config.settings import WORKER_ID

# Настройка логирования
logger = logging.getLogger(__name__)

# Загрузка модели Random Forest
MODEL_PATH = "/models/rf_baseline.pkl"
SCALER_PATH = "/models/scaler.pkl"

def load_model():
    """
    Загружает модель Random Forest и скейлер.
    
    Returns:
        tuple: (модель, скейлер) или (None, None) в случае ошибки
    """
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        logger.info("Модель Random Forest и скейлер успешно загружены")
        return model, scaler
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {e}")
        return None, None

# Загрузка модели при инициализации
model, scaler = load_model()

def validate_data(data: Dict[str, Any]) -> bool:
    """
    Валидирует входные данные для ML задачи.
    
    Args:
        data: Входные данные для валидации
        
    Returns:
        bool: True, если данные валидны, иначе False
    """
    try:
        # Проверяем наличие необходимых полей
        if not isinstance(data, dict):
            logger.error("Данные не являются словарем")
            return False
        
        required_fields = ["prediction_id", "user_id", "data"]
        for field in required_fields:
            if field not in data:
                logger.error(f"Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем, что data содержит транзакцию
        if not isinstance(data["data"], dict) or "transaction" not in data["data"]:
            logger.error("В данных отсутствует транзакция для анализа")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при валидации данных: {e}")
        return False

def prepare_transaction_features(transaction_data: Dict[str, Any]) -> Union[pd.DataFrame, None]:
    """
    Подготавливает данные транзакции для предсказания
    
    Args:
        transaction_data: Данные транзакции
        
    Returns:
        pd.DataFrame: Подготовленные признаки или None в случае ошибки
    """
    try:
        # Создаем DataFrame из данных транзакции
        df = pd.DataFrame([transaction_data])
        
        # Применяем скейлер, если он есть
        if scaler:
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if not numeric_cols.empty:
                df[numeric_cols] = scaler.transform(df[numeric_cols])
        
        return df
    except Exception as e:
        logger.error(f"Ошибка при подготовке данных транзакции: {e}")
        return None

def predict_transaction(features: pd.DataFrame) -> Dict[str, Any]:
    """
    Выполняет предсказание для транзакции
    
    Args:
        features: Подготовленные признаки транзакции
        
    Returns:
        dict: Результат предсказания
    """
    try:
        if model is None:
            return {
                "prediction": "Ошибка: модель не загружена",
                "is_fraud": False,
                "probability": 0.0,
                "error": "Model not loaded"
            }
        
        # Получаем вероятности классов (не мошенническая [0] и мошенническая [1])
        probabilities = model.predict_proba(features)
        fraud_probability = float(probabilities[0][1])
        
        # Получаем предсказание класса (0 - не мошенническая, 1 - мошенническая)
        prediction = model.predict(features)[0]
        is_fraud = bool(prediction == 1)
        
        result = {
            "prediction": "Мошенническая транзакция" if is_fraud else "Легитимная транзакция",
            "is_fraud": is_fraud,
            "fraud_probability": fraud_probability,
            "confidence": round(fraud_probability if is_fraud else (1 - fraud_probability), 4)
            }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        return {
            "prediction": f"Ошибка обработки: {str(e)}",
            "is_fraud": False,
            "fraud_probability": 0.0,
            "error": str(e)
        }

def make_prediction(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет предсказание на основе входных данных.
    
    Args:
        input_data: Входные данные
        
    Returns:
        dict: Результат предсказания
    """
    try:
        processing_start = datetime.now()
        
        # Извлекаем данные транзакции
        if "transaction" not in input_data:
            raise ValueError("Отсутствуют данные транзакции")
            
        transaction_data = input_data["transaction"]
        
        # Подготавливаем данные
        features = prepare_transaction_features(transaction_data)
        if features is None:
            raise ValueError("Не удалось подготовить данные для анализа")
        
        # Выполняем предсказание
        result = predict_transaction(features)
        
        # Добавляем метаданные
        processing_time = (datetime.now() - processing_start).total_seconds()
        result.update({
            "transaction_id": transaction_data.get("id", "unknown"),
            "processing_time": processing_time,
            "worker_id": WORKER_ID,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Предсказание выполнено за {processing_time:.2f} сек. Результат: {result['prediction']}")
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        return {
            "prediction": f"Ошибка: {str(e)}",
            "error": str(e),
            "is_fraud": False,
            "fraud_probability": 0.0,
            "worker_id": WORKER_ID,
            "timestamp": datetime.now().isoformat()
        } 