"""
Общие фикстуры для всех тестов
"""
import pytest
import os
import sys
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="function")
def test_db() -> Generator[str, None, None]:
    """
    Создание временной тестовой БД для каждого теста.
    Каждый тест получает чистую базу данных.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Устанавливаем переменную окружения для тестовой БД
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    
    yield db_path
    
    # Восстанавливаем оригинальный DATABASE_URL
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    elif "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
    
    # Удаляем тестовую БД
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def db_session(test_db) -> Generator[Session, None, None]:
    """
    Создание сессии БД для теста.
    Автоматически создает и удаляет таблицы.
    """
    from storage.db import SessionLocal, Base, engine
    
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    # Создаем сессию
    db = SessionLocal()
    try:
        yield db
        db.rollback()  # Откатываем все изменения
    finally:
        db.close()
    
    # Удаляем таблицы после теста
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db) -> Generator[TestClient, None, None]:
    """
    Создание тестового клиента FastAPI.
    Каждый тест получает чистый клиент с чистой БД.
    """
    from app.src.main import app
    from storage.db import Base, engine
    from storage.repository import create_default_ml_models
    
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    # Создаем дефолтные ML модели
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        create_default_ml_models(session)
    finally:
        session.close()
    
    # Мокируем RabbitMQ publisher для всех тестов на уровне модуля
    with patch('app.src.routers.predict.get_rabbitmq_publisher') as mock_get_publisher:
        mock_publisher = MagicMock()
        mock_publisher.publish_task = MagicMock(return_value=None)
        mock_get_publisher.return_value = mock_publisher
        
        with TestClient(app) as c:
            yield c
    
    # Удаляем таблицы после теста
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def mock_rabbitmq():
    """
    Фикстура для мокирования RabbitMQ publisher.
    Можно использовать в тестах для проверки вызовов.
    """
    with patch('app.src.services.rabbitmq_client.get_rabbitmq_publisher') as mock_get_publisher:
        mock_publisher = MagicMock()
        mock_publisher.publish_task = MagicMock(return_value=None)
        mock_get_publisher.return_value = mock_publisher
        yield mock_publisher


def register_user(client: TestClient, email: str, password: str) -> dict:
    """
    Helper функция для регистрации пользователя.
    Возвращает данные пользователя.
    """
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200, f"Registration failed: {response.text}"
    return response.json()


def login_user(client: TestClient, email: str, password: str) -> str:
    """
    Helper функция для логина пользователя.
    Возвращает JWT токен.
    """
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


def get_auth_headers(token: str) -> dict:
    """
    Helper функция для создания заголовков авторизации.
    """
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def registered_user(client):
    """
    Фикстура для создания зарегистрированного пользователя.
    Возвращает email, password и данные пользователя.
    """
    email = "testuser@example.com"
    password = "testpass123"
    user_data = register_user(client, email, password)
    return {
        "email": email,
        "password": password,
        "user_data": user_data
    }


@pytest.fixture(scope="function")
def authenticated_user(client, registered_user):
    """
    Фикстура для создания аутентифицированного пользователя.
    Возвращает email, password, user_data и token.
    """
    token = login_user(client, registered_user["email"], registered_user["password"])
    return {
        **registered_user,
        "token": token,
        "headers": get_auth_headers(token)
    }


@pytest.fixture(scope="function")
def admin_user(client):
    """
    Фикстура для создания администратора.
    """
    from storage.db import SessionLocal
    from storage.repository import create_user
    
    email = "admin@example.com"
    password = "adminpass123"
    
    # Создаем админа напрямую через репозиторий
    db = SessionLocal()
    try:
        user = create_user(db, email, password, role="admin")
    finally:
        db.close()
    
    token = login_user(client, email, password)
    
    return {
        "email": email,
        "password": password,
        "user_data": {"id": user.id, "email": email, "role": "admin"},
        "token": token,
        "headers": get_auth_headers(token)
    }

