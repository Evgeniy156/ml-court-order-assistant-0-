"""
Smoke тесты для API распознавания СНИЛС
"""
import pytest
import sys
import os
import io
import numpy as np
from PIL import Image
import cv2
from fastapi.testclient import TestClient

# Добавляем путь к app/src
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
_app_src = os.path.join(_project_root, "app", "src")
if _app_src not in sys.path:
    sys.path.insert(0, _app_src)

from main import app


def generate_synthetic_snils_image() -> bytes:
    """
    Генерирует синтетическое изображение с 11 клетками и цифрами.
    """
    # Создаем белое изображение
    width, height = 800, 200
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Параметры клеток
    cell_size = 50
    cell_gap = 10
    start_x = 50
    start_y = 75
    
    # Рисуем 11 клеток
    cells = []
    for i in range(11):
        x = start_x + i * (cell_size + cell_gap)
        y = start_y
        
        # Рисуем рамку клетки
        cv2.rectangle(img, (x, y), (x + cell_size, y + cell_size), (0, 0, 0), 2)
        
        # Генерируем случайную цифру (для теста)
        digit = str(i % 10)
        
        # Рисуем цифру
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 3
        (text_width, text_height), baseline = cv2.getTextSize(
            digit, font, font_scale, thickness
        )
        text_x = x + (cell_size - text_width) // 2
        text_y = y + (cell_size + text_height) // 2
        cv2.putText(
            img, digit, (text_x, text_y), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA
        )
        
        cells.append((x, y, cell_size, cell_size))
    
    # Конвертируем в bytes
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    img_bytes = io.BytesIO()
    pil_img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    
    return img_bytes.getvalue()


@pytest.fixture
def client():
    """Фикстура для тестового клиента"""
    return TestClient(app)


class TestSnilsAPI:
    """Smoke тесты для API распознавания СНИЛС"""
    
    def test_recognize_endpoint_exists(self, client):
        """Тест, что эндпоинт существует"""
        # Отправляем пустой запрос, чтобы проверить, что эндпоинт существует
        # Ожидаем ошибку валидации, но не 404
        response = client.post("/snils/recognize")
        assert response.status_code != 404
    
    def test_recognize_with_image(self, client):
        """Тест распознавания с синтетическим изображением"""
        # Генерируем изображение
        image_bytes = generate_synthetic_snils_image()
        
        # Отправляем запрос
        response = client.post(
            "/snils/recognize",
            files={"file": ("test.png", image_bytes, "image/png")}
        )
        
        # Проверяем статус
        assert response.status_code == 200
        
        # Проверяем структуру ответа
        data = response.json()
        assert "count" in data
        assert "results" in data
        assert "warnings" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["results"], list)
        assert isinstance(data["warnings"], list)
    
    def test_recognize_response_structure(self, client):
        """Тест структуры ответа"""
        image_bytes = generate_synthetic_snils_image()
        
        response = client.post(
            "/snils/recognize",
            files={"file": ("test.png", image_bytes, "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Если найдены результаты, проверяем структуру
        if data["count"] > 0:
            result = data["results"][0]
            assert "snils_digits_masked" in result
            assert "snils_formatted_masked" in result
            assert "is_valid_checksum" in result
            assert "confidence" in result
            assert "warnings" in result
            assert "per_digit" in result
            
            # Проверяем типы
            assert isinstance(result["is_valid_checksum"], bool)
            assert isinstance(result["confidence"], (int, float))
            assert isinstance(result["warnings"], list)
            assert isinstance(result["per_digit"], list)
    
    def test_recognize_invalid_file_type(self, client):
        """Тест с невалидным типом файла"""
        response = client.post(
            "/snils/recognize",
            files={"file": ("test.txt", b"not an image", "text/plain")}
        )
        
        assert response.status_code == 400
    
    def test_recognize_empty_file(self, client):
        """Тест с пустым файлом"""
        response = client.post(
            "/snils/recognize",
            files={"file": ("empty.png", b"", "image/png")}
        )
        
        assert response.status_code == 400
    
    def test_debug_endpoint_disabled(self, client):
        """Тест, что debug эндпоинт отключен по умолчанию"""
        image_bytes = generate_synthetic_snils_image()
        
        response = client.post(
            "/snils/recognize/debug",
            files={"file": ("test.png", image_bytes, "image/png")}
        )
        
        # Должен вернуть 404, если ENABLE_DEBUG_ENDPOINTS не установлен
        assert response.status_code == 404

