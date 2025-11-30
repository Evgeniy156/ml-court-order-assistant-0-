"""
ML Court Order Assistant - FastAPI REST API

Основной модуль приложения с эндпоинтами:
- Регистрация и авторизация пользователей
- Просмотр и пополнение баланса
- Запросы к ML-сервису
- Просмотр истории транзакций и предсказаний
"""
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.hash import bcrypt

# Добавляем корень проекта в sys.path для импорта storage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.db import SessionLocal, engine, Base
from storage.models import UserDB, BillingAccountDB, TransactionDB, MLModelDB
from storage.repository import (
    create_user,
    get_user_by_email,
    deposit_credits,
    withdraw_credits,
    get_user_transactions,
    create_default_ml_models,
)


# ============== Конфигурация ==============
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа


# ============== Lifespan ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация БД при старте и очистка при завершении"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_ml_models(db)
    finally:
        db.close()
    yield


# ============== FastAPI приложение ==============
app = FastAPI(
    title="ML Court Order Assistant",
    description="REST API для системы предсказания судебных приказов",
    version="1.0.0",
    lifespan=lifespan,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ============== Pydantic схемы ==============
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class BalanceResponse(BaseModel):
    user_id: int
    balance: float


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма пополнения (> 0)")


class TransactionResponse(BaseModel):
    id: int
    amount: float
    type: str
    created_at: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


class PredictionRequest(BaseModel):
    """Входные данные для предсказания"""
    total_debt: float = Field(..., gt=0, description="Сумма задолженности")
    penalty_amount: float = Field(..., ge=0, description="Сумма пени")
    days_overdue: int = Field(..., ge=0, description="Дней просрочки")
    payments_ratio: float = Field(..., ge=0, le=1, description="Доля оплаченного (0-1)")
    is_physical_person: bool = Field(..., description="Физическое лицо")


class PredictionResponse(BaseModel):
    prediction: float
    model_name: str
    credits_charged: int
    message: str


# ============== База данных ==============
def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============== JWT функции ==============
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return TokenData(email=email)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> UserDB:
    """Получить текущего пользователя из токена"""
    token_data = verify_token(token)
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ============== Эндпоинты ==============

# --- Главная ---
@app.get("/", tags=["General"])
def read_root():
    """Главная страница с описанием возможностей"""
    return {
        "service": "ML Court Order Assistant",
        "description": "Система предсказания пригодности дел для судебного приказа",
        "features": [
            "Регистрация и авторизация пользователей",
            "Пополнение баланса кредитов",
            "ML-предсказания с оплатой кредитами",
            "Просмотр истории транзакций и предсказаний",
        ],
        "docs": "/docs",
    }


@app.get("/health", tags=["General"])
def health_check():
    """Проверка состояния сервиса"""
    return {"status": "healthy"}


# --- Регистрация и авторизация ---
@app.post("/auth/register", response_model=UserResponse, tags=["Auth"])
def register(user_data: UserCreate, db=Depends(get_db)):
    """Регистрация нового пользователя"""
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    user = create_user(db, user_data.email, user_data.password)
    return user


@app.post("/auth/login", response_model=Token, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """Авторизация пользователя (OAuth2 password flow)"""
    user = get_user_by_email(db, form_data.username)
    if user is None or not bcrypt.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def get_me(current_user: UserDB = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


# --- Баланс ---
@app.get("/balance", response_model=BalanceResponse, tags=["Balance"])
def get_balance(current_user: UserDB = Depends(get_current_user), db=Depends(get_db)):
    """Получить текущий баланс"""
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing account not found",
        )
    
    return BalanceResponse(user_id=current_user.id, balance=float(account.balance))


@app.post("/balance/deposit", response_model=TransactionResponse, tags=["Balance"])
def deposit(
    request: DepositRequest,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """Пополнить баланс (эмуляция платежа)"""
    try:
        tx = deposit_credits(
            db,
            user_id=current_user.id,
            amount=request.amount,
            description="Balance top-up via API",
        )
        return tx
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# --- История транзакций ---
@app.get("/transactions", response_model=List[TransactionResponse], tags=["Transactions"])
def get_transactions(
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """Получить историю транзакций"""
    transactions = get_user_transactions(db, current_user.id)
    return transactions


# --- ML предсказания ---
@app.post("/predict", response_model=PredictionResponse, tags=["ML"])
def predict(
    request: PredictionRequest,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Выполнить ML-предсказание.
    
    Требует достаточного баланса кредитов.
    При успешном предсказании списываются кредиты.
    """
    # Получаем ML модель
    model = db.query(MLModelDB).filter(
        MLModelDB.name == "court_order_suitability_v1"
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ML model not found",
        )
    
    # Проверяем баланс
    account = db.query(BillingAccountDB).filter(
        BillingAccountDB.user_id == current_user.id
    ).first()
    
    if not account or float(account.balance) < model.price_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {model.price_credits}, available: {float(account.balance) if account else 0}",
        )
    
    # Выполняем "предсказание" (простая эвристика для демо)
    prediction_score = calculate_prediction(request)
    
    # Списываем кредиты
    try:
        withdraw_credits(
            db,
            user_id=current_user.id,
            amount=model.price_credits,
            description=f"ML prediction: {model.name}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return PredictionResponse(
        prediction=prediction_score,
        model_name=model.name,
        credits_charged=model.price_credits,
        message="Prediction completed successfully",
    )


def calculate_prediction(data: PredictionRequest) -> float:
    """
    Простая эвристика для расчета вероятности успеха судебного приказа.
    В реальном проекте здесь была бы ML модель.
    """
    score = 0.5
    
    # Сумма долга влияет на вероятность
    if 0 < data.total_debt <= 100000:
        score += 0.2
    elif data.total_debt > 100000:
        score -= 0.1
    
    # Просрочка
    if data.days_overdue > 90:
        score += 0.1
    
    # Физлицо
    if data.is_physical_person:
        score += 0.05
    
    # Доля оплаченного
    score -= data.payments_ratio * 0.2
    
    return max(0.0, min(1.0, score))


@app.get("/models", tags=["ML"])
def list_models(db=Depends(get_db)):
    """Получить список доступных ML моделей"""
    models = db.query(MLModelDB).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "price_credits": m.price_credits,
        }
        for m in models
    ]


# --- Для администраторов (опционально) ---
@app.get("/admin/users", tags=["Admin"])
def list_users(
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """Список всех пользователей (только для админов)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    users = db.query(UserDB).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "balance": float(u.billing_account.balance) if u.billing_account else 0,
        }
        for u in users
    ]


@app.post("/admin/deposit/{user_id}", tags=["Admin"])
def admin_deposit(
    user_id: int,
    request: DepositRequest,
    current_user: UserDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """Пополнить баланс пользователю (только для админов)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    target_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    try:
        tx = deposit_credits(
            db,
            user_id=user_id,
            amount=request.amount,
            description=f"Admin deposit by {current_user.email}",
        )
        return {"message": "Deposit successful", "transaction_id": tx.id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
