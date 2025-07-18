"""
Маршруты для аутентификации пользователей.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.users import Token, User, UserCreate
from app.services.users import authenticate_user, create_user, get_user_by_username
from ml_service.models import Balance

router = APIRouter(tags=["auth"])

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Получение токена доступа.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=User)
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