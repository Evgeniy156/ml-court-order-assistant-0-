#!/usr/bin/env python3
"""
Smoke-тесты для API ML Court Order Assistant.

Сценарий тестирования:
1. health → register (уникальный email) → login (достать JWT) → auth/me
2. deposit(100) → balance(before) → transactions(before count)
3. predict → balance(after должно уменьшиться) → transactions(after count >= before+1)

Использование:
    python scripts/smoke_test_api.py
    BASE_URL=http://localhost:80 python scripts/smoke_test_api.py
    python scripts/smoke_test_api.py --base-url http://localhost:80 --password testpass123
"""
import os
import sys
import time
import uuid
import argparse
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Конфигурация по умолчанию
DEFAULT_BASE_URL = os.getenv("BASE_URL", "http://localhost:80")
DEFAULT_PASSWORD = os.getenv("PASSWORD", "testpass123")
DEFAULT_TIMEOUT = int(os.getenv("TIMEOUT", "10"))

# Exit codes
EXIT_SUCCESS = 0
EXIT_HEALTH_FAIL = 2
EXIT_REGISTER_FAIL = 3
EXIT_LOGIN_FAIL = 4
EXIT_OTHER_FAIL = 5


class SmokeTestRunner:
    """Класс для выполнения smoke-тестов API"""
    
    def __init__(self, base_url: str, password: str, timeout: int):
        self.base_url = base_url.rstrip('/')
        self.password = password
        self.timeout = timeout
        self.email = f"smoke_test_{uuid.uuid4().hex[:8]}@example.com"
        self.token: Optional[str] = None
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Создать сессию с retry стратегией"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _print_step(self, step_name: str, success: bool, details: str = ""):
        """Печатать результат шага"""
        icon = "✅" if success else "❌"
        print(f"{icon} {step_name}")
        if details:
            print(f"   {details}")
    
    def _print_error(self, response: requests.Response):
        """Печатать детали ошибки"""
        print(f"   Status: {response.status_code}")
        try:
            body = response.json()
            print(f"   Body: {body}")
        except:
            print(f"   Body: {response.text[:200]}")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        success_codes: list = [200, 201],
        **kwargs
    ) -> Optional[requests.Response]:
        """Выполнить HTTP запрос с обработкой ошибок"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            response = self.session.request(
                method, 
                url, 
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"   Network error: {e}")
            return None
    
    def test_health(self) -> bool:
        """Тест 1: Проверка health endpoint"""
        print("\n[1/10] Проверка health endpoint...")
        response = self._make_request('GET', '/health')
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                self._print_step("Health check", True, f"Status: {data.get('status')}")
                return True
        
        self._print_step("Health check", False)
        if response:
            self._print_error(response)
        return False
    
    def test_register(self) -> bool:
        """Тест 2: Регистрация нового пользователя"""
        print(f"\n[2/10] Регистрация пользователя {self.email}...")
        response = self._make_request(
            'POST',
            '/auth/register',
            json={
                'email': self.email,
                'password': self.password
            }
        )
        
        if response and response.status_code == 200:
            data = response.json()
            self._print_step("Register", True, f"User ID: {data.get('id')}")
            return True
        
        self._print_step("Register", False)
        if response:
            self._print_error(response)
        return False
    
    def test_login(self) -> bool:
        """Тест 3: Логин и получение JWT токена"""
        print(f"\n[3/10] Логин пользователя {self.email}...")
        response = self._make_request(
            'POST',
            '/auth/login',
            data={
                'username': self.email,
                'password': self.password
            }
        )
        
        if response and response.status_code == 200:
            data = response.json()
            self.token = data.get('access_token')
            if self.token:
                self._print_step("Login", True, "JWT token получен")
                return True
        
        self._print_step("Login", False)
        if response:
            self._print_error(response)
        return False
    
    def test_auth_me(self) -> bool:
        """Тест 4: Проверка auth/me endpoint"""
        print("\n[4/10] Проверка auth/me...")
        response = self._make_request('GET', '/auth/me')
        
        if response and response.status_code == 200:
            data = response.json()
            self._print_step("Auth/me", True, f"Email: {data.get('email')}, Role: {data.get('role')}")
            return True
        
        self._print_step("Auth/me", False)
        if response:
            self._print_error(response)
        return False
    
    def test_deposit(self) -> bool:
        """Тест 5: Пополнение баланса на 100"""
        print("\n[5/10] Пополнение баланса на 100...")
        response = self._make_request(
            'POST',
            '/balance/deposit',
            json={'amount': 100.0}
        )
        
        if response and response.status_code == 200:
            data = response.json()
            self._print_step("Deposit", True, f"Amount: {data.get('amount')}, Type: {data.get('type')}")
            return True
        
        self._print_step("Deposit", False)
        if response:
            self._print_error(response)
        return False
    
    def test_balance_before(self) -> Optional[float]:
        """Тест 6: Получение баланса до predict"""
        print("\n[6/10] Получение баланса (before)...")
        response = self._make_request('GET', '/balance')
        
        if response and response.status_code == 200:
            data = response.json()
            balance = data.get('balance')
            self._print_step("Balance (before)", True, f"Balance: {balance}")
            return balance
        
        self._print_step("Balance (before)", False)
        if response:
            self._print_error(response)
        return None
    
    def test_transactions_before(self) -> int:
        """Тест 7: Получение количества транзакций до predict"""
        print("\n[7/10] Получение транзакций (before)...")
        response = self._make_request('GET', '/transactions')
        
        if response and response.status_code == 200:
            transactions = response.json()
            count = len(transactions)
            self._print_step("Transactions (before)", True, f"Count: {count}")
            return count
        
        self._print_step("Transactions (before)", False)
        if response:
            self._print_error(response)
        return 0
    
    def test_predict(self) -> bool:
        """Тест 8: Создание ML предсказания"""
        print("\n[8/10] Создание ML предсказания...")
        response = self._make_request(
            'POST',
            '/predict',
            json={
                'total_debt': 50000.0,
                'penalty_amount': 5000.0,
                'days_overdue': 90,
                'payments_ratio': 0.3,
                'is_physical_person': True
            }
        )
        
        if response and response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')
            self._print_step("Predict", True, f"Task ID: {task_id}, Status: {data.get('status')}")
            return True
        
        self._print_step("Predict", False)
        if response:
            self._print_error(response)
        return False
    
    def test_balance_after(self, balance_before: Optional[float]) -> bool:
        """Тест 9: Проверка баланса после predict (должен уменьшиться)"""
        print("\n[9/10] Проверка баланса (after)...")
        response = self._make_request('GET', '/balance')
        
        if response and response.status_code == 200:
            data = response.json()
            balance_after = data.get('balance')
            
            if balance_before is not None and balance_after < balance_before:
                self._print_step(
                    "Balance (after)", 
                    True, 
                    f"Balance: {balance_after} (было {balance_before}, уменьшился)"
                )
                return True
            elif balance_before is None:
                self._print_step("Balance (after)", True, f"Balance: {balance_after}")
                return True
            else:
                self._print_step(
                    "Balance (after)", 
                    False, 
                    f"Balance не уменьшился: {balance_after} >= {balance_before}"
                )
                return False
        
        self._print_step("Balance (after)", False)
        if response:
            self._print_error(response)
        return False
    
    def test_transactions_after(self, transactions_before: int) -> bool:
        """Тест 10: Проверка количества транзакций после predict (должно увеличиться)"""
        print("\n[10/10] Проверка транзакций (after)...")
        response = self._make_request('GET', '/transactions')
        
        if response and response.status_code == 200:
            transactions = response.json()
            count_after = len(transactions)
            
            if count_after >= transactions_before + 1:
                self._print_step(
                    "Transactions (after)", 
                    True, 
                    f"Count: {count_after} (было {transactions_before}, увеличилось)"
                )
                return True
            else:
                self._print_step(
                    "Transactions (after)", 
                    False, 
                    f"Count не увеличилось: {count_after} < {transactions_before + 1}"
                )
                return False
        
        self._print_step("Transactions (after)", False)
        if response:
            self._print_error(response)
        return False
    
    def run_all_tests(self) -> int:
        """Запустить все тесты и вернуть exit code"""
        print(f"=" * 60)
        print(f"Smoke Test API: {self.base_url}")
        print(f"Email: {self.email}")
        print(f"=" * 60)
        
        # Тест 1: Health
        if not self.test_health():
            return EXIT_HEALTH_FAIL
        
        # Тест 2: Register
        if not self.test_register():
            return EXIT_REGISTER_FAIL
        
        # Тест 3: Login
        if not self.test_login():
            return EXIT_LOGIN_FAIL
        
        # Тест 4: Auth/me
        if not self.test_auth_me():
            return EXIT_OTHER_FAIL
        
        # Тест 5: Deposit
        if not self.test_deposit():
            return EXIT_OTHER_FAIL
        
        # Тест 6: Balance before
        balance_before = self.test_balance_before()
        if balance_before is None:
            return EXIT_OTHER_FAIL
        
        # Тест 7: Transactions before
        transactions_before = self.test_transactions_before()
        
        # Тест 8: Predict
        if not self.test_predict():
            return EXIT_OTHER_FAIL
        
        # Небольшая задержка для обработки транзакции
        time.sleep(1)
        
        # Тест 9: Balance after
        if not self.test_balance_after(balance_before):
            return EXIT_OTHER_FAIL
        
        # Тест 10: Transactions after (проверка после predict)
        if not self.test_transactions_after(transactions_before):
            return EXIT_OTHER_FAIL
        
        print("\n" + "=" * 60)
        print("✅ Все smoke-тесты пройдены успешно!")
        print("=" * 60)
        return EXIT_SUCCESS


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Smoke-тесты для API ML Court Order Assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python scripts/smoke_test_api.py
  BASE_URL=http://localhost:80 python scripts/smoke_test_api.py
  python scripts/smoke_test_api.py --base-url http://localhost:80 --password testpass123 --timeout 15
        """
    )
    
    parser.add_argument(
        '--base-url',
        type=str,
        default=DEFAULT_BASE_URL,
        help=f'Base URL API (по умолчанию: {DEFAULT_BASE_URL})'
    )
    parser.add_argument(
        '--password',
        type=str,
        default=DEFAULT_PASSWORD,
        help=f'Пароль для тестового пользователя (по умолчанию: {DEFAULT_PASSWORD})'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f'Timeout для запросов в секундах (по умолчанию: {DEFAULT_TIMEOUT})'
    )
    
    args = parser.parse_args()
    
    runner = SmokeTestRunner(
        base_url=args.base_url,
        password=args.password,
        timeout=args.timeout
    )
    
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

