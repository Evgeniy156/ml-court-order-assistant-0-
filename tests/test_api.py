"""
Тесты для REST API ML Court Order Assistant

Покрывает ключевые сценарии:
- Аутентификация (регистрация, логин, JWT)
- Баланс (пополнение, проверка)
- Предсказания (списание кредитов, недостаточно средств)
- Транзакции (история, сортировка)
- Админ-функции (список пользователей, пополнение баланса)
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from tests.conftest import register_user, login_user, get_auth_headers


# ============== Тесты аутентификации ==============

class TestAuth:
    """Тесты авторизации и регистрации"""
    
    def test_auth_register_ok(self, client):
        """Тест успешной регистрации пользователя"""
        # Arrange & Act
        response = client.post(
            "/auth/register",
            json={"email": "newuser@example.com", "password": "password123"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
        assert "id" in data
    
    def test_auth_register_duplicate(self, client):
        """Тест регистрации с дублирующимся email"""
        # Arrange: регистрируем пользователя
        register_user(client, "duplicate@example.com", "password123")
        
        # Act: пытаемся зарегистрировать повторно
        response = client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "password123"}
        )
        
        # Assert
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_auth_login_ok(self, client):
        """Тест успешного логина"""
        # Arrange: регистрируем пользователя
        email = "logintest@example.com"
        password = "password123"
        register_user(client, email, password)
        
        # Act
        response = client.post(
            "/auth/login",
            data={"username": email, "password": password}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    def test_auth_login_wrong_password(self, client):
        """Тест логина с неверным паролем"""
        # Arrange: регистрируем пользователя
        email = "wrongpass@example.com"
        password = "password123"
        register_user(client, email, password)
        
        # Act: пытаемся войти с неверным паролем
        response = client.post(
            "/auth/login",
            data={"username": email, "password": "wrongpassword"}
        )
        
        # Assert
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_auth_me_requires_auth(self, client):
        """Тест что /auth/me требует авторизации"""
        # Act: запрос без токена
        response = client.get("/auth/me")
        
        # Assert
        assert response.status_code == 401
    
    def test_auth_me_with_token(self, client, authenticated_user):
        """Тест получения информации о текущем пользователе"""
        # Act
        response = client.get(
            "/auth/me",
            headers=authenticated_user["headers"]
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == authenticated_user["email"]
        assert data["role"] == "user"
        assert "id" in data


# ============== Тесты баланса ==============

class TestBalance:
    """Тесты баланса и пополнения"""
    
    def test_balance_initial_zero(self, client, authenticated_user):
        """Тест что начальный баланс равен нулю"""
        # Act
        response = client.get(
            "/balance",
            headers=authenticated_user["headers"]
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == 0.0
        assert data["user_id"] == authenticated_user["user_data"]["id"]
    
    def test_balance_deposit_ok(self, client, authenticated_user):
        """Тест успешного пополнения баланса"""
        # Arrange
        deposit_amount = 100.0
        
        # Act
        response = client.post(
            "/balance/deposit",
            headers=authenticated_user["headers"],
            json={"amount": deposit_amount}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == deposit_amount
        assert data["type"] == "deposit"
        assert "id" in data
        assert "created_at" in data
        
        # Проверяем, что баланс изменился
        balance_response = client.get(
            "/balance",
            headers=authenticated_user["headers"]
        )
        assert balance_response.status_code == 200
        assert balance_response.json()["balance"] == deposit_amount
    
    def test_balance_deposit_invalid(self, client, authenticated_user):
        """Тест пополнения с недопустимой суммой"""
        # Act: отрицательная сумма
        response = client.post(
            "/balance/deposit",
            headers=authenticated_user["headers"],
            json={"amount": -10}
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
        
        # Act: нулевая сумма
        response = client.post(
            "/balance/deposit",
            headers=authenticated_user["headers"],
            json={"amount": 0}
        )
        
        # Assert
        assert response.status_code == 422
    
    def test_balance_requires_auth(self, client):
        """Тест что /balance требует авторизации"""
        # Act
        response = client.get("/balance")
        
        # Assert
        assert response.status_code == 401


# ============== Тесты предсказаний ==============

class TestPredict:
    """Тесты ML предсказаний"""
    
    def test_predict_deducts_balance_and_creates_transaction(
        self, client, authenticated_user
    ):
        """Тест что /predict списывает баланс и создает транзакцию"""
        # Arrange (мок RabbitMQ уже применен в conftest.py)
        
        # Пополняем баланс
        deposit_response = client.post(
            "/balance/deposit",
            headers=authenticated_user["headers"],
            json={"amount": 50}
        )
        assert deposit_response.status_code == 200
        
        # Получаем начальный баланс
        balance_before = client.get(
            "/balance",
            headers=authenticated_user["headers"]
        ).json()["balance"]
        
        # Получаем модель для проверки цены
        models_response = client.get("/models")
        assert models_response.status_code == 200
        model = next(m for m in models_response.json() if m["name"] == "court_order_suitability_v1")
        model_price = model["price_credits"]
        
        # Act: создаем задачу предсказания
        response = client.post(
            "/predict",
            headers=authenticated_user["headers"],
            json={
                "total_debt": 50000.0,
                "penalty_amount": 5000.0,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        
        # Проверяем, что баланс уменьшился
        balance_after = client.get(
            "/balance",
            headers=authenticated_user["headers"]
        ).json()["balance"]
        assert balance_after == balance_before - model_price
        
        # Проверяем, что транзакция создана
        transactions_response = client.get(
            "/transactions",
            headers=authenticated_user["headers"]
        )
        assert transactions_response.status_code == 200
        transactions = transactions_response.json()
        
        # Должна быть транзакция типа withdraw
        withdraw_txs = [tx for tx in transactions if tx["type"] == "withdraw"]
        assert len(withdraw_txs) > 0
        assert any(abs(tx["amount"]) == model_price for tx in withdraw_txs)
    
    def test_predict_insufficient_funds(self, client):
        """Тест предсказания при недостаточном балансе"""
        # Arrange: создаем нового пользователя без баланса
        email = "pooruser@example.com"
        password = "password123"
        register_user(client, email, password)
        token = login_user(client, email, password)
        headers = get_auth_headers(token)
        
        # Act: пытаемся создать задачу без баланса
        response = client.post(
            "/predict",
            headers=headers,
            json={
                "total_debt": 50000.0,
                "penalty_amount": 5000.0,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        
        # Assert
        assert response.status_code == 402  # Payment Required
        assert "insufficient" in response.json()["detail"].lower()
        
        # Проверяем, что баланс остался нулевым
        balance_response = client.get("/balance", headers=headers)
        assert balance_response.json()["balance"] == 0.0
    
    def test_predict_requires_auth(self, client):
        """Тест что /predict требует авторизации"""
        # Act
        response = client.post(
            "/predict",
            json={
                "total_debt": 50000.0,
                "penalty_amount": 5000.0,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        
        # Assert
        assert response.status_code == 401


# ============== Тесты транзакций ==============

class TestTransactions:
    """Тесты истории транзакций"""
    
    def test_transactions_contains_deposit_and_withdraw_and_sorted(
        self, client, authenticated_user
    ):
        """Тест что транзакции содержат deposit и withdraw и отсортированы"""
        # Arrange (мок RabbitMQ уже применен в conftest.py)
        
        # Создаем несколько транзакций
        # 1. Пополнение
        deposit1 = client.post(
            "/balance/deposit",
            headers=authenticated_user["headers"],
            json={"amount": 100}
        )
        assert deposit1.status_code == 200
        
        # 2. Еще одно пополнение
        deposit2 = client.post(
            "/balance/deposit",
            headers=authenticated_user["headers"],
            json={"amount": 50}
        )
        assert deposit2.status_code == 200
        
        # 3. Предсказание (списание)
        models_response = client.get("/models")
        model = next(m for m in models_response.json() if m["name"] == "court_order_suitability_v1")
        
        predict_response = client.post(
            "/predict",
            headers=authenticated_user["headers"],
            json={
                "total_debt": 50000.0,
                "penalty_amount": 5000.0,
                "days_overdue": 120,
                "payments_ratio": 0.3,
                "is_physical_person": True
            }
        )
        assert predict_response.status_code == 200
        
        # Act: получаем историю транзакций
        response = client.get(
            "/transactions",
            headers=authenticated_user["headers"]
        )
        
        # Assert
        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) >= 3
        
        # Проверяем наличие deposit транзакций
        deposit_txs = [tx for tx in transactions if tx["type"] == "deposit"]
        assert len(deposit_txs) >= 2
        
        # Проверяем наличие withdraw транзакций
        withdraw_txs = [tx for tx in transactions if tx["type"] == "withdraw"]
        assert len(withdraw_txs) >= 1
        
        # Проверяем сортировку (по убыванию created_at)
        for i in range(len(transactions) - 1):
            assert transactions[i]["created_at"] >= transactions[i + 1]["created_at"]
        
        # Проверяем суммы
        assert any(tx["amount"] == 100.0 for tx in deposit_txs)
        assert any(tx["amount"] == 50.0 for tx in deposit_txs)
        assert any(abs(tx["amount"]) == model["price_credits"] for tx in withdraw_txs)
    
    def test_transactions_requires_auth(self, client):
        """Тест что /transactions требует авторизации"""
        # Act
        response = client.get("/transactions")
        
        # Assert
        assert response.status_code == 401


# ============== Тесты админ-функций ==============

class TestAdmin:
    """Тесты административных функций"""
    
    def test_admin_users_requires_admin(self, client, authenticated_user):
        """Тест что /admin/users требует прав администратора"""
        # Act: обычный пользователь пытается получить список пользователей
        response = client.get(
            "/admin/users",
            headers=authenticated_user["headers"]
        )
        
        # Assert
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
    
    def test_admin_users_with_admin(self, client, admin_user):
        """Тест получения списка пользователей администратором"""
        # Arrange: создаем еще одного пользователя
        register_user(client, "regular@example.com", "password123")
        
        # Act
        response = client.get(
            "/admin/users",
            headers=admin_user["headers"]
        )
        
        # Assert
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 2  # Админ + обычный пользователь
        
        # Проверяем структуру ответа
        for user in users:
            assert "id" in user
            assert "email" in user
            assert "role" in user
            assert "balance" in user
    
    def test_admin_deposit_changes_user_balance(self, client, admin_user):
        """Тест что админ может пополнить баланс пользователю"""
        # Arrange: создаем обычного пользователя
        regular_email = "regular2@example.com"
        register_user(client, regular_email, "password123")
        regular_token = login_user(client, regular_email, "password123")
        regular_headers = get_auth_headers(regular_token)
        
        # Получаем ID пользователя
        me_response = client.get("/auth/me", headers=regular_headers)
        user_id = me_response.json()["id"]
        
        # Проверяем начальный баланс
        balance_before = client.get("/balance", headers=regular_headers).json()["balance"]
        assert balance_before == 0.0
        
        # Act: админ пополняет баланс
        deposit_amount = 200.0
        response = client.post(
            f"/admin/deposit/{user_id}",
            headers=admin_user["headers"],
            json={"amount": deposit_amount}
        )
        
        # Assert
        assert response.status_code == 200
        assert "transaction_id" in response.json()
        
        # Проверяем, что баланс изменился
        balance_after = client.get("/balance", headers=regular_headers).json()["balance"]
        assert balance_after == deposit_amount
        
        # Проверяем транзакцию
        transactions = client.get("/transactions", headers=regular_headers).json()
        assert len(transactions) > 0
        assert any(
            tx["type"] == "deposit" and tx["amount"] == deposit_amount
            for tx in transactions
        )
    
    def test_admin_deposit_requires_admin(self, client, authenticated_user):
        """Тест что /admin/deposit требует прав администратора"""
        # Arrange: получаем ID пользователя
        me_response = client.get("/auth/me", headers=authenticated_user["headers"])
        user_id = me_response.json()["id"]
        
        # Act: обычный пользователь пытается пополнить баланс
        response = client.post(
            f"/admin/deposit/{user_id}",
            headers=authenticated_user["headers"],
            json={"amount": 100}
        )
        
        # Assert
        assert response.status_code == 403
    
    def test_admin_deposit_user_not_found(self, client, admin_user):
        """Тест пополнения баланса несуществующему пользователю"""
        # Act
        response = client.post(
            "/admin/deposit/99999",
            headers=admin_user["headers"],
            json={"amount": 100}
        )
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
