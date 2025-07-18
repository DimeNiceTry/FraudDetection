"""
Маршруты для работы с предсказаниями.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.predictions import PredictionRequest, PredictionResponse, PredictionHistory
from app.services.db import get_db
from app.services.auth import get_current_user
from app.services.predictions import create_prediction, get_prediction, get_user_predictions
from ml_service.models.users.user import User

router = APIRouter(tags=["predictions"])


@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового предсказания.
    """
    try:
        prediction = create_prediction(db, current_user.id, request.data)
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction_by_id(
    prediction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение информации о предсказании по ID.
    """
    try:
        prediction = get_prediction(db, prediction_id, current_user.id)
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=PredictionHistory)
async def get_user_prediction_history(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение истории предсказаний пользователя.
    """
    predictions = get_user_predictions(db, current_user.id, skip, limit)
    return {"predictions": predictions} 