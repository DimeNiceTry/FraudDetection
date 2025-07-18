"""
Маршруты для предсказаний.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.models.prediction import PredictionRequest, PredictionResponse, PredictionHistory
from app.services.auth_service import get_current_user
from app.services.prediction_service import create_prediction, get_prediction, get_user_predictions

# Настройка роутера
router = APIRouter(tags=["predictions"])

@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Создание нового предсказания.
    """
    try:
        prediction = create_prediction(current_user.id, request.data)
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction_by_id(
    prediction_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о предсказании по ID.
    """
    try:
        prediction = get_prediction(prediction_id, current_user.id)
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=PredictionHistory)
async def get_user_prediction_history(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Получение истории предсказаний пользователя.
    """
    try:
        predictions = get_user_predictions(current_user.id, skip, limit)
        return {"predictions": predictions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 