"""
Маршруты для работы с пользователями.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.schemas.users import User, UserCreate, Token
from app.services.db import get_db
from app.services.auth import authenticate_user, create_access_token, get_current_user
from app.services.users import create_user, get_user_by_username

router = APIRouter(tags=["users"])


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Получение токена доступа.
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users", response_model=User)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    """
    try:
        db_user = create_user(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """
    return current_user 