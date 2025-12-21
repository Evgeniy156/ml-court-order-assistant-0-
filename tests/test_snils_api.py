"""
Тесты для API распознавания СНИЛС.
"""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Определяем путь к тестовым изображениям
TEST_ASSETS_DIR = Path(__file__).parent / "assets_local"
SNILS1_PATH = TEST_ASSETS_DIR / "snils1.jpg"
SNILS2_PATH = TEST_ASSETS_DIR / "snils2.jpg"


@pytest.fixture
def client():
    """Создает тестового клиента FastAPI."""
    from app.src.main import app
    return TestClient(app)


def test_snils_recognize_snils2(client):
    """
    Тест распознавания на snils2.jpg.
    Ожидается: HTTP 200 с count >= 1 (если модель есть) или HTTP 503 (если модели нет)
    """
    if not SNILS2_PATH.exists():
        pytest.skip(f"Тестовое изображение не найдено: {SNILS2_PATH}")
    
    with open(SNILS2_PATH, "rb") as f:
        response = client.post(
            "/snils/recognize",
            files={"file": ("snils2.jpg", f, "image/jpeg")}
        )
    
    # Если модель отсутствует, ожидаем 503
    if response.status_code == 503:
        result = response.json()
        assert "detail" in result
        assert "weights not found" in result["detail"].lower()
        return  # Тест пройден для случая отсутствия модели
    
    assert response.status_code == 200, f"Ожидался HTTP 200 или 503, получен {response.status_code}"
    
    result = response.json()
    assert "count" in result
    assert "results" in result
    assert "warnings" in result
    
    assert result["count"] >= 1, f"Ожидалось count >= 1, получено {result['count']}"
    
    # Проверяем структуру результатов
    if result["count"] > 0:
        for row_result in result["results"]:
            assert "snils_digits_masked" in row_result
            assert "snils_formatted_masked" in row_result
            assert "is_valid_checksum" in row_result
            assert "confidence" in row_result
            assert "warnings" in row_result
            assert "per_digit" in row_result


def test_snils_recognize_snils1(client):
    """
    Тест распознавания на snils1.jpg.
    Ожидается: не падать, warnings не пустые (если count=0) или HTTP 503 (если модели нет)
    """
    if not SNILS1_PATH.exists():
        pytest.skip(f"Тестовое изображение не найдено: {SNILS1_PATH}")
    
    with open(SNILS1_PATH, "rb") as f:
        response = client.post(
            "/snils/recognize",
            files={"file": ("snils1.jpg", f, "image/jpeg")}
        )
    
    # Если модель отсутствует, ожидаем 503
    if response.status_code == 503:
        result = response.json()
        assert "detail" in result
        assert "weights not found" in result["detail"].lower()
        return  # Тест пройден для случая отсутствия модели
    
    assert response.status_code == 200, f"Ожидался HTTP 200 или 503, получен {response.status_code}"
    
    result = response.json()
    assert "count" in result
    assert "results" in result
    assert "warnings" in result
    
    # Если count=0, должны быть warnings
    if result["count"] == 0:
        assert len(result["warnings"]) > 0, "При count=0 должны быть warnings"


def test_snils_recognize_schema(client):
    """
    Тест схемы ответа API.
    """
    if not SNILS2_PATH.exists():
        pytest.skip(f"Тестовое изображение не найдено: {SNILS2_PATH}")
    
    with open(SNILS2_PATH, "rb") as f:
        response = client.post(
            "/snils/recognize",
            files={"file": ("snils2.jpg", f, "image/jpeg")}
        )
    
    # Если модель отсутствует, ожидаем 503
    if response.status_code == 503:
        result = response.json()
        assert "detail" in result
        assert "weights not found" in result["detail"].lower()
        return  # Тест пройден для случая отсутствия модели
    
    assert response.status_code == 200
    
    result = response.json()
    
    # Проверяем обязательные поля
    assert "count" in result
    assert isinstance(result["count"], int)
    assert result["count"] >= 0
    
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) == result["count"]
    
    assert "warnings" in result
    assert isinstance(result["warnings"], list)
    
    # Проверяем структуру результатов
    for row_result in result["results"]:
        assert "snils_digits_masked" in row_result
        assert isinstance(row_result["snils_digits_masked"], str)
        
        assert "snils_formatted_masked" in row_result
        assert isinstance(row_result["snils_formatted_masked"], str)
        
        assert "is_valid_checksum" in row_result
        assert isinstance(row_result["is_valid_checksum"], bool)
        
        assert "confidence" in row_result
        assert isinstance(row_result["confidence"], (int, float))
        assert 0 <= row_result["confidence"] <= 1
        
        assert "warnings" in row_result
        assert isinstance(row_result["warnings"], list)
        
        assert "per_digit" in row_result
        assert isinstance(row_result["per_digit"], list)
        assert len(row_result["per_digit"]) == 11  # 11 клеток


def test_snils_recognize_debug(client):
    """
    Тест debug эндпоинта (только если ENABLE_DEBUG_ENDPOINTS=true).
    """
    if not os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        pytest.skip("Debug эндпоинт отключен (ENABLE_DEBUG_ENDPOINTS != true)")
    
    if not SNILS2_PATH.exists():
        pytest.skip(f"Тестовое изображение не найдено: {SNILS2_PATH}")
    
    with open(SNILS2_PATH, "rb") as f:
        response = client.post(
            "/snils/recognize/debug",
            files={"file": ("snils2.jpg", f, "image/jpeg")}
        )
    
    assert response.status_code == 200
    
    result = response.json()
    
    # Проверяем структуру debug ответа
    assert "angle" in result
    assert "method" in result
    assert "qr_count" in result
    assert "qr_boxes" in result
    assert "rows_count" in result
    assert "warnings" in result
    assert "rows_boxes" in result
    
    # Проверяем, что НЕ возвращаются распознанные цифры
    assert "snils_digits_masked" not in result
    assert "results" not in result or len(result.get("results", [])) == 0


def test_snils_recognize_invalid_file(client):
    """
    Тест обработки невалидного файла.
    """
    # Отправляем не изображение
    response = client.post(
        "/snils/recognize",
        files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    
    assert response.status_code == 400


def test_snils_recognize_empty_file(client):
    """
    Тест обработки пустого файла.
    """
    response = client.post(
        "/snils/recognize",
        files={"file": ("empty.jpg", b"", "image/jpeg")}
    )
    
    # Может быть 400 или 200 с count=0
    assert response.status_code in [200, 400]

