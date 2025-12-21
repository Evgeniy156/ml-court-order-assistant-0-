"""
Быстрая проверка работы API.
"""
import os
import requests
import time
import sys

BASE_URL = os.getenv("API_URL", "http://localhost:8001")

def test_health():
    """Проверка health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Health endpoint работает: {response.json()}")
            return True
        else:
            print(f"✗ Health endpoint вернул {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Не удалось подключиться к {BASE_URL}")
        print("  Убедитесь, что API запущен: uvicorn app.src.main:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def test_snils_recognize():
    """Проверка распознавания СНИЛС"""
    try:
        test_image = "tests/assets_local/snils2.jpg"
        with open(test_image, "rb") as f:
            files = {"file": ("snils2.jpg", f, "image/jpeg")}
            response = requests.post(f"{BASE_URL}/snils/recognize", files=files, timeout=10)
        
        print(f"\nСтатус: {response.status_code}")
        
        if response.status_code == 503:
            result = response.json()
            print(f"✓ Правильно возвращает 503 при отсутствии модели")
            print(f"  Сообщение: {result.get('detail', 'N/A')}")
            return True
        elif response.status_code == 200:
            result = response.json()
            print(f"✓ Распознавание работает")
            print(f"  Найдено строк: {result.get('count', 0)}")
            if result.get('count', 0) > 0:
                print(f"  Первый результат: {result['results'][0].get('snils_formatted_masked', 'N/A')}")
            return True
        else:
            print(f"✗ Неожиданный статус: {response.status_code}")
            print(f"  Ответ: {response.text[:200]}")
            return False
    except FileNotFoundError:
        print(f"✗ Тестовое изображение не найдено: {test_image}")
        return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Проверка работы API")
    print("=" * 50)
    
    print("\n1. Проверка health endpoint...")
    health_ok = test_health()
    
    if not health_ok:
        print("\n⚠ API не запущен. Запустите:")
        print("  uvicorn app.src.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    print("\n2. Проверка распознавания СНИЛС...")
    recognize_ok = test_snils_recognize()
    
    print("\n" + "=" * 50)
    if health_ok and recognize_ok:
        print("✓ Все проверки пройдены")
    else:
        print("✗ Некоторые проверки не пройдены")
    print("=" * 50)

