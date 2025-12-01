"""Роутер авторизации: регистрация, логин, текущий пользователь"""
import os
import sys

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.hash import bcrypt

# Добавляем корень проекта в sys.path
sys. path.insert(0, os. path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from storage.db import SessionLocal
from storage.models import UserDB
from storage.repository import create_user, get_user_by_email

from .. schemas import UserCreate, UserResponse, Token
from ..services import create_access_token, verify_token, oauth2_scheme


router = APIRouter(prefix="/auth", tags=["Auth"])


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db. close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> UserDB:
    """Получить текущего пользователя из токена"""
    token_data = verify_token(token)
    user = get_user_by_email(db, token_data. email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db=Depends(get_db)):
    """Регистрация нового пользователя"""
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status. HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = create_user(db, user_data. email, user_data. password)
    return user


@router. post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """Авторизация пользователя (OAuth2 password flow)"""
    user = get_user_by_email(db, form_data.username)
    if user is None or not bcrypt.verify(form_data. password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserDB = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user