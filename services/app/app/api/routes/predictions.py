"""
Маршруты для работы с предсказаниями ML моделей.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.security import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.schemas.users import User
from app.schemas.predictions import PredictionRequest, PredictionResponse, PredictionHistory
from app.services.predictions import create_prediction, get_prediction_by_id, get_user_predictions
from app.services.balances import check_and_decrease_balance
from app.services.rabbitmq import publish_message

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создать новое предсказание.
    """
    # Проверяем баланс и списываем средства
    cost = settings.PREDICTION_COST
    if not check_and_decrease_balance(db, current_user.id, cost):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Недостаточно средств на балансе"
        )
    
    try:
        # Создаем запись о предсказании
        prediction = create_prediction(db, current_user.id, request.data, cost)
        
        # Отправляем задачу в очередь
        message = {
            "prediction_id": prediction.id,
            "user_id": current_user.id,
            "data": request.data
        }
        if not publish_message(message, settings.ML_TASK_QUEUE):
            # В случае ошибки отправки в очередь
            prediction.status = "failed"
            db.commit()
            
            # Возвращаем средства пользователю
            from app.services.transactions import add_to_balance
            add_to_balance(
                db, 
                current_user.id, 
                cost, 
                f"Возврат средств за предсказание {prediction.id} (ошибка отправки в очередь)",
                prediction.id
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при отправке задачи в очередь"
            )
        
        return PredictionResponse(
            prediction_id=prediction.id,
            status=prediction.status,
            result=prediction.result,
            created_at=prediction.created_at,
            completed_at=prediction.completed_at,
            cost=prediction.cost
        )
    except Exception as e:
        # В случае любой другой ошибки, пытаемся вернуть средства
        from app.services.transactions import add_to_balance
        try:
            add_to_balance(
                db, 
                current_user.id, 
                cost, 
                f"Возврат средств из-за ошибки создания предсказания: {str(e)}",
                None
            )
        except Exception as refund_error:
            # Если не удалось вернуть средства, логируем ошибку
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при возврате средств: {refund_error}")
        
        # Прокидываем исходную ошибку дальше
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при создании предсказания: {str(e)}"
            )

@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить данные предсказания по ID.
    """
    prediction = get_prediction_by_id(db, prediction_id)
    
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предсказание не найдено"
        )
    
    if prediction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому предсказанию"
        )
    
    return PredictionResponse(
        prediction_id=prediction.id,
        status=prediction.status,
        result=prediction.result,
        created_at=prediction.created_at,
        completed_at=prediction.completed_at,
        cost=prediction.cost
    )

@router.get("/", response_model=PredictionHistory)
async def get_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Получить историю предсказаний пользователя.
    """
    predictions = get_user_predictions(db, current_user.id, skip, limit)
    
    return PredictionHistory(
        predictions=[
            PredictionResponse(
                prediction_id=p.id,
                status=p.status,
                result=p.result,
                created_at=p.created_at,
                completed_at=p.completed_at,
                cost=p.cost
            ) for p in predictions
        ]
    ) 