"""
Скрипт для проверки системы распознавания СНИЛС.
"""
import sys
import os

# Добавляем корень проекта в путь
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def check_imports():
    """Проверяет, что все модули импортируются."""
    print("Проверка импортов...")
    try:
        from app.src.services.snils.pipeline import run_snils_pipeline
        print("✓ pipeline импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта pipeline: {e}")
        return False
    
    try:
        from app.src.services.snils.digit_model import get_model
        print("✓ digit_model импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта digit_model: {e}")
        return False
    
    try:
        from app.src.services.snils.grid_detect import detect_snils_rows
        print("✓ grid_detect импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта grid_detect: {e}")
        return False
    
    return True

def check_model():
    """Проверяет наличие модели."""
    print("\nПроверка модели...")
    weights_path = os.path.join(project_root, "weights", "snils_digits.pt")
    if os.path.exists(weights_path):
        print(f"✓ Модель найдена: {weights_path}")
        return True
    else:
        print(f"✗ Модель не найдена: {weights_path}")
        print("  Ожидается HTTP 503 при запросе к /snils/recognize")
        return False

def check_health():
    """Проверяет health endpoint."""
    print("\nПроверка health endpoint...")
    try:
        from app.src.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        if response.status_code == 200:
            print(f"✓ Health endpoint работает: {response.json()}")
            return True
        else:
            print(f"✗ Health endpoint вернул {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Ошибка проверки health: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Проверка системы распознавания СНИЛС")
    print("=" * 50)
    
    all_ok = True
    all_ok &= check_imports()
    all_ok &= check_model()
    all_ok &= check_health()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ Все проверки пройдены")
    else:
        print("✗ Некоторые проверки не пройдены")
    print("=" * 50)

