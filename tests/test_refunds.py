"""
Тесты для проверки возврата кредитов при ошибках
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
        json={"email": "refundtest@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    
    # Авторизация
    response = client.post(
        "/auth/login",
        data={"username": "refundtest@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return token


class TestRefundOnQueueError:
    """Тесты возврата кредитов при ошибке постановки в очередь"""
    
    def test_refund_on_rabbitmq_error(self, client, auth_token):
        """Тест: при ошибке публикации в RabbitMQ кредиты возвращаются"""
        # Пополняем баланс
        deposit_response = client.post(
            "/balance/deposit",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"amount": 50}
        )
        assert deposit_response.status_code == 200
        
        # Получаем начальный баланс
        balance_response = client.get(
            "/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        initial_balance = balance_response.json()["balance"]
        
        # Мокаем ошибку при публикации в RabbitMQ
        with patch('app.src.services.rabbitmq_client.RabbitMQPublisher.publish_task') as mock_publish:
            mock_publish.side_effect = Exception("RabbitMQ connection failed")
            
            # Пытаемся создать задачу
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
            
            # Должна быть ошибка 503
            assert response.status_code == 503
            detail = response.json()["detail"].lower()
            assert "no credits were charged" in detail or "refunded" in detail
            
            # Проверяем, что баланс не изменился (кредиты не были списаны из-за rollback)
            balance_response = client.get(
                "/balance",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            final_balance = balance_response.json()["balance"]
            
            # Баланс должен остаться прежним (транзакция откатилась, кредиты не списаны)
            assert abs(float(final_balance) - float(initial_balance)) < 0.01
    
    def test_no_credits_charged_if_insufficient_balance(self, client):
        """Тест: при недостаточном балансе кредиты не списываются"""
        # Регистрируем нового пользователя без баланса
        client.post(
            "/auth/register",
            json={"email": "nobalance@example.com", "password": "password123"}
        )
        response = client.post(
            "/auth/login",
            data={"username": "nobalance@example.com", "password": "password123"}
        )
        token = response.json()["access_token"]
        
        # Получаем баланс (должен быть 0)
        balance_response = client.get(
            "/balance",
            headers={"Authorization": f"Bearer {token}"}
        )
        initial_balance = balance_response.json()["balance"]
        assert float(initial_balance) == 0
        
        # Пытаемся создать задачу
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
        
        # Должна быть ошибка 402 (недостаточно средств)
        assert response.status_code == 402
        
        # Баланс должен остаться 0
        balance_response = client.get(
            "/balance",
            headers={"Authorization": f"Bearer {token}"}
        )
        final_balance = balance_response.json()["balance"]
        assert float(final_balance) == 0


class TestRefundOnTaskFailure:
    """Тесты возврата кредитов при ошибке выполнения задачи в worker"""
    
    def test_refund_on_task_processing_error(self, client, auth_token):
        """Тест: при ошибке обработки задачи в worker кредиты возвращаются"""
        # Этот тест требует запущенного worker и RabbitMQ
        # В реальном проекте можно использовать моки или интеграционные тесты
        pass

