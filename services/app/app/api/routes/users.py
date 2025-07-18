"""
Маршруты для работы с пользователями.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.users import User, UserCreate
from app.services.users import create_user, get_user_by_username
from ml_service.models import Balance

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Получить данные текущего пользователя.
    """
    return current_user

@router.post("/", response_model=User)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    """
    try:
        # Проверяем, существует ли пользователь с таким именем
        db_user = get_user_by_username(db, username=user_data.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует"
            )
        
        # Создаем пользователя
        user = create_user(db, user_data)
        
        # Создаем баланс для пользователя (если эта логика не в create_user)
        try:
            balance = db.query(Balance).filter(Balance.user_id == user.id).first()
            if not balance:
                balance = Balance(user_id=user.id, amount=10.0)  # Начальный баланс 10.0
                db.add(balance)
                db.commit()
        except Exception as e:
            print(f"Ошибка при создании баланса: {e}")
        
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 