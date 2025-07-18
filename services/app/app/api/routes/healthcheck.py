"""
Маршруты для проверки состояния сервиса.
"""
from fastapi import APIRouter

router = APIRouter(tags=["system"])

@router.get("/")
async def root():
    """
    Корневой эндпоинт.
    """
    return {"message": "ML Service API работает"}

@router.get("/health")
async def health_check():
    """
    Эндпоинт для проверки здоровья сервиса.
    """
    return {"status": "ok"} 