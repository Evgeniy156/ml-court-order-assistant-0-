"""
Простая проверка системы без pytest.
"""
import sys
import os
from pathlib import Path

# Определяем корень проекта
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

print(f"Рабочая директория: {os.getcwd()}")
print(f"Корень проекта: {script_dir}")

# Проверка 1: Импорты
print("\n1. Проверка импортов...")
try:
    from app.src.main import app
    print("  ✓ app импортирован")
except Exception as e:
    print(f"  ✗ Ошибка импорта app: {e}")
    sys.exit(1)

try:
    from app.src.services.snils.pipeline import run_snils_pipeline
    print("  ✓ pipeline импортирован")
except Exception as e:
    print(f"  ✗ Ошибка импорта pipeline: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Проверка 2: Health endpoint
print("\n2. Проверка health endpoint...")
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    if response.status_code == 200:
        print("  ✓ Health endpoint работает")
    else:
        print("  ✗ Health endpoint не работает")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Ошибка проверки health: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Проверка 3: Модель
print("\n3. Проверка модели...")
weights_path = script_dir / "weights" / "snils_digits.pt"
if weights_path.exists():
    print(f"  ✓ Модель найдена: {weights_path}")
else:
    print(f"  ⚠ Модель не найдена: {weights_path}")
    print("  Ожидается HTTP 503 при запросе к /snils/recognize")

# Проверка 4: Тест без модели (должен вернуть 503)
print("\n4. Проверка обработки отсутствия модели...")
try:
    test_image_path = script_dir / "tests" / "assets_local" / "snils2.jpg"
    if test_image_path.exists():
        with open(test_image_path, "rb") as f:
            response = client.post(
                "/snils/recognize",
                files={"file": ("snils2.jpg", f, "image/jpeg")}
            )
        print(f"  Status: {response.status_code}")
        if response.status_code == 503:
            print("  ✓ Правильно возвращает 503 при отсутствии модели")
            print(f"  Message: {response.json().get('detail', 'N/A')}")
        elif response.status_code == 200:
            print("  ✓ Распознавание работает (модель найдена)")
        else:
            print(f"  ⚠ Неожиданный статус: {response.status_code}")
    else:
        print(f"  ⚠ Тестовое изображение не найдено: {test_image_path}")
except Exception as e:
    print(f"  ✗ Ошибка проверки распознавания: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Проверка завершена")
print("=" * 50)

