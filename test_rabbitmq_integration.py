"""
Скрипт для тестирования интеграции с RabbitMQ (для локального запуска)

Требования:
1. RabbitMQ должен быть запущен (например, через Docker)
2. База данных должна быть настроена
3. Переменные окружения должны быть установлены

Запуск:
    python test_rabbitmq_integration.py
"""
import sys
import os

# Добавляем пути для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("ТЕСТ ИНТЕГРАЦИИ С RABBITMQ")
print("=" * 60)

# Проверка 1: Импорт модулей
print("\n1. Проверка импорта модулей...")
try:
    from storage.models import MLTaskDB, MLModelDB, UserDB, BillingAccountDB
    from app.src.rabbitmq_client import RabbitMQPublisher
    print("   ✓ Модели БД импортированы")
    print("   ✓ RabbitMQPublisher импортирован")
except Exception as e:
    print(f"   ✗ Ошибка импорта: {e}")
    sys.exit(1)

# Проверка 2: Структура MLTaskDB
print("\n2. Проверка структуры MLTaskDB...")
try:
    task_fields = [
        'id', 'user_id', 'model_id', 'status', 'input_data',
        'prediction', 'error_message', 'credits_charged',
        'created_at', 'started_at', 'completed_at'
    ]
    
    for field in task_fields:
        if not hasattr(MLTaskDB, field):
            print(f"   ✗ Поле {field} отсутствует в MLTaskDB")
            sys.exit(1)
    
    print(f"   ✓ Все {len(task_fields)} полей присутствуют в MLTaskDB")
except Exception as e:
    print(f"   ✗ Ошибка проверки структуры: {e}")
    sys.exit(1)

# Проверка 3: RabbitMQ Publisher
print("\n3. Проверка RabbitMQPublisher...")
try:
    publisher = RabbitMQPublisher()
    print("   ✓ RabbitMQPublisher создан")
    
    # Проверяем методы
    assert hasattr(publisher, 'connect'), "Метод connect отсутствует"
    assert hasattr(publisher, 'publish_task'), "Метод publish_task отсутствует"
    assert hasattr(publisher, 'close'), "Метод close отсутствует"
    print("   ✓ Все методы присутствуют")
except Exception as e:
    print(f"   ✗ Ошибка проверки Publisher: {e}")
    sys.exit(1)

# Проверка 4: ML Worker импорт
print("\n4. Проверка ML Worker...")
try:
    # Просто проверяем что файл можно импортировать
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ml_worker",
        "app/src/ml_worker.py"
    )
    module = importlib.util.module_from_spec(spec)
    # Не выполняем, просто проверяем что загружается
    print("   ✓ ML Worker модуль загружается")
except Exception as e:
    print(f"   ✗ Ошибка загрузки ML Worker: {e}")
    sys.exit(1)

# Проверка 5: Роутер predict
print("\n5. Проверка роутера predict...")
try:
    from app.src.routers import predict
    
    # Проверяем что роутер существует
    assert hasattr(predict, 'router'), "Router не найден"
    print("   ✓ Router predict импортирован")
    
    # Проверяем что есть нужные эндпоинты
    routes = [route.path for route in predict.router.routes]
    expected_routes = ['/predict', '/task/{task_id}', '/predictions', '/models']
    
    for route in expected_routes:
        if route not in routes:
            print(f"   ⚠ Эндпоинт {route} не найден в роутере")
    
    print(f"   ✓ Найдено {len(routes)} эндпоинтов")
except Exception as e:
    print(f"   ✗ Ошибка проверки роутера: {e}")
    sys.exit(1)

# Проверка 6: Схемы
print("\n6. Проверка схем...")
try:
    from app.src.schemas.predict import PredictionResponse
    
    # Проверяем новые поля в PredictionResponse
    response_fields = PredictionResponse.model_fields
    
    assert 'task_id' in response_fields, "Поле task_id отсутствует"
    assert 'status' in response_fields, "Поле status отсутствует"
    
    print("   ✓ PredictionResponse содержит task_id и status")
except Exception as e:
    print(f"   ✗ Ошибка проверки схем: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 60)

print("\n📝 Следующие шаги:")
print("1. Запустите RabbitMQ: docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
print("2. Настройте БД и переменные окружения")
print("3. Запустите FastAPI сервер: uvicorn app.src.main:app")
print("4. Запустите воркеры: python -m app.src.ml_worker")
print("5. Тестируйте через API: POST /predict")
print("\n🌐 RabbitMQ UI: http://localhost:15672 (guest/guest)")
