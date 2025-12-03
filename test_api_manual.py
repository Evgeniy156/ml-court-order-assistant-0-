"""
Скрипт для ручного тестирования API с RabbitMQ интеграцией

Этот скрипт демонстрирует:
1. Регистрацию и авторизацию пользователя
2. Пополнение баланса
3. Отправку задачи на предсказание (через RabbitMQ)
4. Проверку статуса задачи
5. Просмотр истории предсказаний

Требования:
- FastAPI сервер должен быть запущен
- RabbitMQ должен быть запущен
- Хотя бы один ML worker должен быть запущен
"""
import requests
import time
import json
from typing import Optional

# Конфигурация
API_BASE_URL = "http://localhost:8000"  # или http://localhost:80 если через nginx


class MLCourtAPI:
    """Клиент для работы с API"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def register(self, email: str, password: str) -> dict:
        """Регистрация нового пользователя"""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={"email": email, "password": password}
        )
        return response.json()
    
    def login(self, email: str, password: str) -> str:
        """Авторизация и получение токена"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        data = response.json()
        self.token = data.get("access_token")
        return self.token
    
    def get_balance(self) -> dict:
        """Получить баланс"""
        response = requests.get(
            f"{self.base_url}/balance",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()
    
    def deposit(self, amount: float) -> dict:
        """Пополнить баланс"""
        response = requests.post(
            f"{self.base_url}/balance/deposit",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"amount": amount}
        )
        return response.json()
    
    def predict(self, input_data: dict) -> dict:
        """Отправить задачу на предсказание"""
        response = requests.post(
            f"{self.base_url}/predict",
            headers={"Authorization": f"Bearer {self.token}"},
            json=input_data
        )
        return response.json()
    
    def get_task_status(self, task_id: int) -> dict:
        """Получить статус задачи"""
        response = requests.get(
            f"{self.base_url}/task/{task_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()
    
    def get_predictions_history(self) -> list:
        """Получить историю предсказаний"""
        response = requests.get(
            f"{self.base_url}/predictions",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()


def print_section(title: str):
    """Красивый вывод раздела"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    """Основной сценарий тестирования"""
    print("🧪 ТЕСТ API С RABBITMQ ИНТЕГРАЦИЕЙ")
    
    # Инициализация клиента
    api = MLCourtAPI()
    
    # Генерируем уникальный email для теста
    import random
    test_email = f"test_user_{random.randint(1000, 9999)}@example.com"
    test_password = "password123"
    
    # Шаг 1: Регистрация
    print_section("1. Регистрация пользователя")
    try:
        result = api.register(test_email, test_password)
        print(f"✓ Пользователь зарегистрирован: {test_email}")
        print(f"  User ID: {result.get('id')}")
    except Exception as e:
        print(f"✗ Ошибка регистрации: {e}")
        return
    
    # Шаг 2: Авторизация
    print_section("2. Авторизация")
    try:
        token = api.login(test_email, test_password)
        print(f"✓ Авторизация успешна")
        print(f"  Token: {token[:50]}...")
    except Exception as e:
        print(f"✗ Ошибка авторизации: {e}")
        return
    
    # Шаг 3: Проверка баланса
    print_section("3. Проверка баланса")
    try:
        balance = api.get_balance()
        print(f"✓ Текущий баланс: {balance.get('balance')} кредитов")
    except Exception as e:
        print(f"✗ Ошибка получения баланса: {e}")
        return
    
    # Шаг 4: Пополнение баланса
    print_section("4. Пополнение баланса")
    try:
        result = api.deposit(100.0)
        print(f"✓ Баланс пополнен на 100 кредитов")
        print(f"  Новый баланс: {result.get('new_balance')} кредитов")
    except Exception as e:
        print(f"✗ Ошибка пополнения: {e}")
        return
    
    # Шаг 5: Отправка задачи на предсказание
    print_section("5. Отправка ML-задачи в очередь")
    prediction_input = {
        "total_debt": 75000.0,
        "penalty_amount": 7500.0,
        "days_overdue": 150,
        "payments_ratio": 0.2,
        "is_physical_person": True
    }
    
    try:
        result = api.predict(prediction_input)
        task_id = result.get('task_id')
        print(f"✓ Задача отправлена в очередь")
        print(f"  Task ID: {task_id}")
        print(f"  Статус: {result.get('status')}")
        print(f"  Списано кредитов: {result.get('credits_charged')}")
        print(f"  Сообщение: {result.get('message')}")
    except Exception as e:
        print(f"✗ Ошибка отправки задачи: {e}")
        return
    
    # Шаг 6: Проверка статуса задачи (с ожиданием)
    print_section("6. Проверка статуса задачи")
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        try:
            status_data = api.get_task_status(task_id)
            status = status_data.get('status')
            
            print(f"  Попытка {attempt + 1}/{max_attempts}: статус = {status}")
            
            if status == 'completed':
                print(f"\n✓ Задача выполнена успешно!")
                print(f"  Предсказание: {status_data.get('prediction')}")
                print(f"  Входные данные: {json.dumps(status_data.get('input_data'), indent=2, ensure_ascii=False)}")
                print(f"  Время создания: {status_data.get('created_at')}")
                print(f"  Время начала: {status_data.get('started_at')}")
                print(f"  Время завершения: {status_data.get('completed_at')}")
                break
            elif status == 'failed':
                print(f"\n✗ Задача завершилась с ошибкой")
                print(f"  Ошибка: {status_data.get('error_message')}")
                break
            elif status in ['pending', 'processing']:
                print(f"    Задача в процессе обработки, ожидание 2 сек...")
                time.sleep(2)
                attempt += 1
            else:
                print(f"  Неизвестный статус: {status}")
                break
        except Exception as e:
            print(f"✗ Ошибка проверки статуса: {e}")
            break
    
    if attempt >= max_attempts:
        print(f"\n⚠ Превышено время ожидания")
        print(f"  Проверьте что ML workers запущены и работают")
    
    # Шаг 7: Просмотр истории предсказаний
    print_section("7. История предсказаний")
    try:
        history = api.get_predictions_history()
        print(f"✓ Найдено {len(history)} предсказаний")
        
        for i, pred in enumerate(history[:3], 1):
            print(f"\n  Предсказание {i}:")
            print(f"    ID: {pred.get('id')}")
            print(f"    Результат: {pred.get('prediction')}")
            print(f"    Сумма долга: {pred.get('total_debt')} руб.")
            print(f"    Дата: {pred.get('created_at')}")
    except Exception as e:
        print(f"✗ Ошибка получения истории: {e}")
    
    # Итоги
    print_section("ТЕСТ ЗАВЕРШЕН")
    print("✓ Основной сценарий выполнен успешно")
    print("\n📝 Проверьте:")
    print("  1. RabbitMQ UI: http://localhost:15672")
    print("  2. Swagger UI: http://localhost:8000/docs")
    print("  3. Логи ML workers для подтверждения обработки")


if __name__ == "__main__":
    print("⚠ ВНИМАНИЕ: Убедитесь что запущены:")
    print("  - FastAPI сервер (uvicorn app.src.main:app)")
    print("  - RabbitMQ")
    print("  - Хотя бы один ML worker (python -m app.src.ml_worker)")
    print("\nНажмите Enter для продолжения или Ctrl+C для отмены...")
    
    try:
        input()
        main()
    except KeyboardInterrupt:
        print("\n\nТест отменен")
    except Exception as e:
        print(f"\n\n✗ Неожиданная ошибка: {e}")
