"""
Поиск строк из 11 квадратных клеток на изображении.
Использует контуры, aspect ratio и clustering по Y.
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

try:
    from sklearn.cluster import DBSCAN
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from .preprocess import preprocess_multi_pass, deskew_image


def detect_qr_codes(image_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Детектирует QR-коды на изображении (опционально, для подсказки геометрии).
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        Список bbox QR-кодов: [(x, y, w, h), ...]
    """
    qr_detector = cv2.QRCodeDetector()
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(gray)
    
    qr_boxes = []
    if retval and points is not None:
        if isinstance(points, np.ndarray):
            if len(points.shape) == 3:
                for point_set in points:
                    if point_set is not None and len(point_set.shape) == 2 and point_set.shape[0] == 4:
                        x_coords = [int(p[0]) for p in point_set]
                        y_coords = [int(p[1]) for p in point_set]
                        x = min(x_coords)
                        y = min(y_coords)
                        w = max(x_coords) - x
                        h = max(y_coords) - y
                        qr_boxes.append((x, y, w, h))
    
    return qr_boxes


def detect_cells_by_contours(image_bgr: np.ndarray) -> List[List[Tuple[int, int, int, int]]]:
    """
    Детектирует строки из 11 клеток по контурам.
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        Список строк; каждая строка = 11 bbox (x, y, w, h)
    """
    # Пробуем несколько вариантов предобработки
    preprocessed_variants = preprocess_multi_pass(image_bgr)
    
    all_cells = []
    
    for binary, method_name in preprocessed_variants:
        # Морфология для соединения разрывов
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary_processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary_processed = cv2.morphologyEx(binary_processed, cv2.MORPH_OPEN, kernel)
        
        # Находим контуры
        contours, _ = cv2.findContours(binary_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        h, w = binary.shape
        min_area = (h * w) * 0.0001
        max_area = (h * w) * 0.1
        
        cells = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue
            
            # Проверяем прямоугольность
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) != 4:
                continue
            
            x, y, w_box, h_box = cv2.boundingRect(contour)
            aspect = w_box / h_box if h_box > 0 else 0
            if aspect < 0.7 or aspect > 1.3:  # Квадратные клетки
                continue
            
            # Проверяем заполненность
            bbox_area = w_box * h_box
            if bbox_area > 0:
                fill_ratio = area / bbox_area
                if fill_ratio < 0.3:
                    continue
            
            cells.append((x, y, w_box, h_box))
        
        if len(cells) >= 11:
            all_cells.extend(cells)
    
    if len(all_cells) < 11:
        return []
    
    # Удаляем дубликаты (близкие клетки)
    unique_cells = []
    for cell in all_cells:
        x1, y1, w1, h1 = cell
        is_duplicate = False
        for existing in unique_cells:
            x2, y2, w2, h2 = existing
            # Проверяем перекрытие
            overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap_area = overlap_x * overlap_y
            area1 = w1 * h1
            area2 = w2 * h2
            if overlap_area > 0.7 * min(area1, area2):  # 70% перекрытие = дубликат
                is_duplicate = True
                break
        if not is_duplicate:
            unique_cells.append(cell)
    
    if len(unique_cells) < 11:
        return []
    
    # Группируем по строкам (clustering по Y)
    cells_with_y = [(x, y, w, h, y + h // 2) for x, y, w, h in unique_cells]
    
    if HAS_SKLEARN:
        y_centers = np.array([[c[4]] for c in cells_with_y])
        # DBSCAN для группировки по Y
        clustering = DBSCAN(eps=h * 0.02, min_samples=5).fit(y_centers)
        labels = clustering.labels_
    else:
        # Fallback: простая группировка по Y
        cells_with_y.sort(key=lambda c: c[4])
        labels = []
        current_label = 0
        current_y = cells_with_y[0][4]
        y_tolerance = h * 0.02
        for cell in cells_with_y:
            if abs(cell[4] - current_y) > y_tolerance:
                current_label += 1
                current_y = cell[4]
            labels.append(current_label)
    
    # Группируем по кластерам
    rows_dict = {}
    for i, label in enumerate(labels):
        if label == -1:  # Шум
            continue
        if label not in rows_dict:
            rows_dict[label] = []
        rows_dict[label].append(cells_with_y[i][:4])
    
    # Ищем последовательности из 11 клеток в каждой строке
    result_rows = []
    for label, row_cells in rows_dict.items():
        if len(row_cells) < 11:
            continue
        
        # Сортируем по X
        row_sorted = sorted(row_cells, key=lambda c: c[0])
        
        # Ищем последовательность из 11 клеток
        for i in range(len(row_sorted) - 10):
            candidate = row_sorted[i:i+11]
            
            # Проверяем размеры (должны быть похожи)
            sizes = [w * h for x, y, w, h in candidate]
            avg_size = np.mean(sizes)
            size_variance = np.std(sizes) / avg_size if avg_size > 0 else 1
            
            if size_variance > 0.3:
                continue
            
            # Проверяем промежутки (должны быть примерно одинаковые)
            gaps = []
            for j in range(len(candidate) - 1):
                x1, _, w1, _ = candidate[j]
                x2, _, _, _ = candidate[j + 1]
                gap = x2 - (x1 + w1)
                gaps.append(gap)
            
            if len(gaps) > 0:
                avg_gap = np.mean(gaps)
                gap_variance = np.std(gaps) / avg_gap if avg_gap > 0 else 1
                
                if gap_variance > 0.5:
                    continue
            
            result_rows.append(candidate)
            break  # Нашли строку, переходим к следующему кластеру
    
    return result_rows


def detect_snils_rows(image_bgr: np.ndarray, debug: bool = False) -> Tuple[List[List[Tuple[int, int, int, int]]], Dict[str, Any]]:
    """
    Детектирует строки СНИЛС на изображении.
    Использует QR-коды как подсказку (опционально) + контуры (обязательно).
    
    Args:
        image_bgr: изображение в формате BGR
        debug: включить debug информацию
        
    Returns:
        (rows, debug_info) где:
        - rows: список строк; каждая строка = 11 bbox (x, y, w, h)
        - debug_info: словарь с отладочной информацией
    """
    debug_info = {
        "method": None,
        "angle": 0.0,
        "qr_count": 0,
        "qr_boxes": [],
        "rows_count": 0,
    }
    
    # Авто-поворот
    image_rotated, angle = deskew_image(image_bgr)
    debug_info["angle"] = float(angle)
    
    # Пробуем найти QR-коды (опционально, для подсказки)
    qr_boxes = detect_qr_codes(image_rotated)
    debug_info["qr_count"] = len(qr_boxes)
    debug_info["qr_boxes"] = [(int(x), int(y), int(w), int(h)) for x, y, w, h in qr_boxes]
    
    # Основной метод: поиск по контурам (обязательно, даже если QR не найден)
    rows = detect_cells_by_contours(image_rotated)
    debug_info["method"] = "contours"
    debug_info["rows_count"] = len(rows)
    
    # Добавляем bbox строк
    debug_info["rows_boxes"] = [
        [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for x, y, w, h in row]
        for row in rows
    ]
    
    return rows, debug_info

