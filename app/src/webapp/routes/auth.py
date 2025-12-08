"""
Роутер для авторизации в WebUI
JWT токены через куки
"""
import os
import sys
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import bcrypt as bcrypt_lib

# Добавляем корень проекта в sys.path для импорта storage
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from storage.db import SessionLocal
from storage.models import UserDB
from storage.repository import create_user, get_user_by_email
from ..services import get_user_by_id

router = APIRouter()

# Настройка шаблонов
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_from_cookie(request: Request, db=Depends(get_db)) -> Optional[UserDB]:
    """Получить текущего пользователя из куки"""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        user_id_int = int(user_id)
        return get_user_by_id(db, user_id_int)
    except (ValueError, TypeError):
        return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user=Depends(get_current_user_from_cookie),
):
    """Страница входа"""
    # Если уже авторизован, перенаправляем на главную
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "current_user": None, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    db=Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    """Обработка входа"""
    user = get_user_by_email(db, email)
    
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный email или пароль"},
            status_code=401
        )
    
    # Проверяем пароль
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    if not bcrypt_lib.checkpw(password_bytes, user.hashed_password.encode('utf-8')):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный email или пароль"},
            status_code=401
        )
    
    # Создаем ответ с редиректом
    response = RedirectResponse(url="/", status_code=303)
    # Устанавливаем куку с user_id
    response.set_cookie(
        key="user_id",
        value=str(user.id),
        max_age=86400 * 7,  # 7 дней
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user=Depends(get_current_user_from_cookie),
):
    """Страница регистрации"""
    # Если уже авторизован, перенаправляем на главную
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "current_user": None, "error": None}
    )


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    db=Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    """Обработка регистрации"""
    # Проверяем, существует ли пользователь
    existing = get_user_by_email(db, email)
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пользователь с таким email уже существует"},
            status_code=400
        )
    
    # Создаем пользователя
    try:
        user = create_user(db, email, password)
        # Автоматически логиним пользователя
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="user_id",
            value=str(user.id),
            max_age=86400 * 7,  # 7 дней
            httponly=True,
            samesite="lax"
        )
        return response
    except Exception as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"Ошибка регистрации: {str(e)}"},
            status_code=500
        )


@router.get("/logout", response_class=HTMLResponse)
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="user_id")
    return response
