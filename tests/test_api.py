"""
Тесты для REST API ML Court Order Assistant
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os
import tempfile

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def test_db():
    """Создание временной тестовой БД"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    
    yield db_path
    
    # Очистка
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def client(test_db):
    """Создание тестового клиента"""
    from app.src.main import app
    from storage.db import Base, engine
    
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as c:
        yield c
    
    # Очистка
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def auth_token(client):
    """Получить токен авторизации"""
    # Регистрация
    response = client.post(
        "/auth/register",
        json={"email": "testuser@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    
    # Авторизация
    response = client.post(
        "/auth/login",
        data={"username": "testuser@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return token


class TestGeneral:
    """Тесты общих эндпоинтов"""
    
    def test_root(self, client):
        """Тест главной страницы"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ML Court Order Assistant"
        assert "features" in data
    
    def test_health(self, client):
        """Тест health check"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuth:
    """Тесты авторизации"""
    
    def test_register_new_user(self, client):
        """Тест регистрации нового пользователя"""
        response = client.post(
            "/auth/register",
            json={"email": "newuser@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
    
    def test_register_duplicate_email(self, client):
        """Тест регистрации с существующим email"""
        # Сначала регистрируем
        client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "password123"}
        )
        # Пытаемся зарегистрировать повторно
        response = client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "password123"}
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_login_success(self, client):
        """Тест успешной авторизации"""
        # Регистрируем
        client.post(
            "/auth/register",
            json={"email": "logintest@example.com", "password": "password123"}
        )
        # Авторизуемся
        response = client.post(
            "/auth/login",
            data={"username": "logintest@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_login_wrong_password(self, client):
        """Тест авторизации с неверным паролем"""
        response = client.post(
            "/auth/login",
            data={"username": "logintest@example.com", "password": "wrongpass"}
        )
        assert response.status_code == 401
    
    def test_get_me(self, client, auth_token):
        """Тест получения информации о текущем пользователе"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "testuser@example.com"


class TestBalance:
    """Тесты баланса"""
    
    def test_get_balance(self, client, auth_token):
        """Тест получения баланса"""
        response = client.get(
            "/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert "balance" in response.json()
    
    def test_deposit(self, client, auth_token):
        """Тест пополнения баланса"""
        response = client.post(
            "/balance/deposit",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"amount": 100}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 100
        assert data["type"] == "deposit"
    
    def test_deposit_invalid_amount(self, client, auth_token):
        """Тест пополнения с недопустимой суммой"""
        response = client.post(
            "/balance/deposit",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"amount": -10}
        )
        assert response.status_code == 422  # Validation error
    
    def test_unauthorized_balance(self, client):
        """Тест доступа к балансу без авторизации"""
        response = client.get("/balance")
        assert response.status_code == 401


class TestTransactions:
    """Тесты истории транзакций"""
    
    def test_get_transactions(self, client, auth_token):
        """Тест получения истории транзакций"""
        response = client.get(
            "/transactions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestPrediction:
    """Тесты ML предсказаний"""
    
    @patch('app.src.routers.predict.get_rabbitmq_publisher')
    def test_predict_success(self, mock_get_publisher, client, auth_token):
        """Тест успешного создания задачи"""
        # Мокируем RabbitMQ publisher
        mock_publisher = MagicMock()
        mock_publisher.publish_task = MagicMock(return_value=None)
        mock_get_publisher.return_value = mock_publisher
        
        # Сначала пополняем баланс
        client.post(
            "/balance/deposit",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"amount": 50}
        )
        
        # Создаем задачу
        response = client.post(
            "/predict",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "total_debt": 50000,
                "penalty_amount": 5000,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] == "pending"
        # Проверяем, что publish_task был вызван
        assert mock_publisher.publish_task.called
    
    def test_predict_insufficient_balance(self, client):
        """Тест предсказания без достаточного баланса"""
        # Регистрируем нового пользователя без баланса
        client.post(
            "/auth/register",
            json={"email": "pooruser@example.com", "password": "password123"}
        )
        response = client.post(
            "/auth/login",
            data={"username": "pooruser@example.com", "password": "password123"}
        )
        token = response.json()["access_token"]
        
        # Пытаемся сделать предсказание
        response = client.post(
            "/predict",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "total_debt": 50000,
                "penalty_amount": 5000,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        assert response.status_code == 402  # Payment required
    
    @patch('app.src.routers.predict.get_rabbitmq_publisher')
    def test_get_task_status(self, mock_get_publisher, client, auth_token):
        """Тест получения статуса задачи"""
        # Мокируем RabbitMQ publisher
        mock_publisher = MagicMock()
        mock_publisher.publish_task = MagicMock(return_value=None)
        mock_get_publisher.return_value = mock_publisher
        
        # Пополняем баланс
        client.post(
            "/balance/deposit",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"amount": 50}
        )
        
        # Создаем задачу
        response = client.post(
            "/predict",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "total_debt": 50000,
                "penalty_amount": 5000,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Получаем статус задачи
        response = client.get(
            f"/task/{task_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert "status" in data
        assert "credits_charged" in data


class TestModels:
    """Тесты ML моделей"""
    
    def test_list_models(self, client):
        """Тест получения списка моделей"""
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
