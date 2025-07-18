"""
Маршруты для пользователей.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import User, UserCreate, Token
from app.services.auth_service import get_current_user, create_access_token
from app.services.user_service import create_user
from app.services.auth_service import authenticate_user
from datetime import timedelta

# Настройка роутера
router = APIRouter(tags=["users"])

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Получение токена аутентификации.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users", response_model=User)
async def register_user(user: UserCreate):
    """
    Регистрация нового пользователя.
    """
    try:
        return create_user(user.username, user.email, user.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """
    return current_user 