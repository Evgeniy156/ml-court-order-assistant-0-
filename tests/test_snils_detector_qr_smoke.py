"""
Smoke тесты для QR-детектора СНИЛС
"""
import pytest
import sys
import os
import numpy as np
from unittest.mock import MagicMock, patch

# Добавляем путь к app/src
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
_app_src = os.path.join(_project_root, "app", "src")
if _app_src not in sys.path:
    sys.path.insert(0, _app_src)

from app.src.services.snils_detector import detect_snils_rows, detect_qr_codes, detect_cells_from_qr


class TestQRDetector:
    """Тесты QR-детектора"""
    
    def test_detect_qr_codes_mock(self):
        """Тест детекции QR-кодов с моком"""
        # Создаем тестовое изображение
        image_bgr = np.zeros((800, 1200, 3), dtype=np.uint8)
        image_bgr[:] = 255  # Белый фон
        
        # Мокаем cv2.QRCodeDetector
        with patch('cv2.QRCodeDetector') as mock_qr_detector_class:
            mock_detector = MagicMock()
            mock_qr_detector_class.return_value = mock_detector
            
            # Настраиваем мок для возврата одного QR
            # detectAndDecodeMulti возвращает (retval, decoded_info, points, straight_qrcode)
            mock_points = np.array([[
                [100, 100],
                [200, 100],
                [200, 200],
                [100, 200]
            ]], dtype=np.float32)
            
            mock_detector.detectAndDecodeMulti.return_value = (
                True,  # retval
                ["test"],  # decoded_info
                [mock_points],  # points
                None  # straight_qrcode
            )
            
            # Вызываем функцию
            qr_boxes = detect_qr_codes(image_bgr)
            
            # Проверяем результат
            assert len(qr_boxes) == 1
            x, y, w, h = qr_boxes[0]
            assert x == 100
            assert y == 100
            assert w == 100
            assert h == 100
    
    def test_detect_cells_from_qr_basic(self):
        """Тест детекции клеток относительно QR"""
        # Создаем тестовое изображение
        image_bgr = np.zeros((800, 1200, 3), dtype=np.uint8)
        image_bgr[:] = 255  # Белый фон
        
        # QR bbox: (100, 100, 50, 50)
        qr_box = (100, 100, 50, 50)
        
        # Вызываем функцию
        cells = detect_cells_from_qr(image_bgr, qr_box, auto_calibrate=False)
        
        # Проверяем результат
        assert cells is not None
        assert len(cells) == 11
        
        # Проверяем, что все клетки в границах изображения
        img_h, img_w = image_bgr.shape[:2]
        for x, y, w, h in cells:
            assert x >= 0
            assert y >= 0
            assert x + w <= img_w
            assert y + h <= img_h
    
    def test_detect_cells_from_qr_out_of_bounds(self):
        """Тест, когда клетки выходят за границы"""
        # Создаем маленькое изображение
        image_bgr = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # QR в правом верхнем углу
        qr_box = (80, 10, 20, 20)
        
        # Вызываем функцию
        cells = detect_cells_from_qr(image_bgr, qr_box, auto_calibrate=False)
        
        # Должен вернуть None, так как клетки выходят за границы
        assert cells is None
    
    def test_detect_snils_rows_with_qr_mock(self):
        """Тест полного детектора с моком QR"""
        # Создаем тестовое изображение
        image_bgr = np.zeros((800, 1200, 3), dtype=np.uint8)
        image_bgr[:] = 255
        
        # Мокаем QR детектор
        with patch('app.src.services.snils_detector.detect_qr_codes') as mock_detect_qr:
            # Возвращаем один QR
            mock_detect_qr.return_value = [(100, 100, 50, 50)]
            
            # Мокаем detect_cells_from_qr
            with patch('app.src.services.snils_detector.detect_cells_from_qr') as mock_detect_cells:
                # Возвращаем 11 клеток
                mock_cells = [(200 + i * 30, 120, 25, 25) for i in range(11)]
                mock_detect_cells.return_value = mock_cells
                
                # Вызываем детектор
                rows, debug_info = detect_snils_rows(image_bgr, debug=True)
                
                # Проверяем результат
                assert len(rows) == 1
                assert len(rows[0]) == 11
                assert debug_info["method"] == "qr"
                assert debug_info["qr_count"] == 1
                assert debug_info["rows_count"] == 1
    
    def test_detect_snils_rows_fallback_contours(self):
        """Тест fallback на контурный детектор"""
        # Создаем тестовое изображение
        image_bgr = np.zeros((800, 1200, 3), dtype=np.uint8)
        image_bgr[:] = 255
        
        # Мокаем QR детектор, чтобы не находил QR
        with patch('app.src.services.snils_detector.detect_qr_codes') as mock_detect_qr:
            mock_detect_qr.return_value = []
            
            # Вызываем детектор
            rows, debug_info = detect_snils_rows(image_bgr, debug=True)
            
            # Проверяем, что использован fallback
            assert debug_info["method"] == "contours"
            assert debug_info["qr_count"] == 0

