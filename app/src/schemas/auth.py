"""Схемы для авторизации и пользователей"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Данные для регистрации пользователя"""
    email: EmailStr
    password: str = Field(..., min_length=4)


class UserResponse(BaseModel):
    """Ответ с данными пользователя"""
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT токен"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Данные из токена"""
    email: Optional[str] = None