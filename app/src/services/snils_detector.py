"""
Улучшенный детектор строк СНИЛС на изображении.
Использует QR-коды как якорь, с fallback на контурный детектор.
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional


def preprocess_for_detection(image_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Предобработка изображения для детекции.
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        (gray, binary, debug_meta) где:
        - gray: grayscale изображение
        - binary: бинарное изображение
        - debug_meta: метаданные для отладки
    """
    h, w = image_bgr.shape[:2]
    debug_meta = {"original_size": (w, h)}
    
    # Нормализация размера: приводим к ширине 1200-1800px
    target_width = 1500
    if w > 2000:
        scale = target_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        image_bgr = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        debug_meta["resized"] = True
        debug_meta["scale"] = scale
    else:
        debug_meta["resized"] = False
    
    # Конвертируем в grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # CLAHE для выравнивания контраста
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Bilateral blur для сохранения краев
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Adaptive threshold
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Морфология для соединения разрывов
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    return gray, binary, debug_meta


def deskew(image_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Автоматический поворот изображения для выравнивания.
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        (rotated_image, angle) где angle в градусах
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # Находим контуры для определения угла
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # HoughLines для определения доминирующего угла
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is not None and len(lines) > 0:
        angles = []
        # cv2.HoughLines возвращает массив формы (N, 1, 2)
        for line in lines[:min(50, len(lines))]:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            # Нормализуем угол в диапазон [-45, 45]
            if angle > 45:
                angle -= 90
            elif angle < -45:
                angle += 90
            angles.append(angle)
        
        if angles:
            # Берем медианный угол
            median_angle = np.median(angles)
            # Поворачиваем только если угол значительный (> 2 градуса)
            if abs(median_angle) > 2:
                h, w = image_bgr.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(image_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated, median_angle
    
    # Если не удалось определить угол, возвращаем исходное изображение
    return image_bgr, 0.0


def detect_qr_codes(image_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Детектирует QR-коды на изображении.
    Пробует несколько вариантов предобработки для улучшения детекции.
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        Список bbox QR-кодов: [(x, y, w, h), ...]
    """
    qr_detector = cv2.QRCodeDetector()
    qr_boxes = []
    
    # Вариант 1: Оригинальное grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(gray)
    
    qr_boxes = []
    if retval and points is not None:
        # Обрабатываем points (может быть разной формы)
        if isinstance(points, np.ndarray):
            if len(points.shape) == 3:  # (N, 1, 2) или (N, 4, 2)
                for point_set in points:
                    if point_set is not None:
                        # Преобразуем в плоский массив точек
                        if len(point_set.shape) == 2:
                            if point_set.shape[0] == 4:  # 4 точки
                                x_coords = [int(p[0]) for p in point_set]
                                y_coords = [int(p[1]) for p in point_set]
                                x = min(x_coords)
                                y = min(y_coords)
                                w = max(x_coords) - x
                                h = max(y_coords) - y
                                qr_boxes.append((x, y, w, h))
            elif len(points.shape) == 2:  # (N, 2) - массив точек
                if len(points) >= 4:
                    x_coords = [int(p[0]) for p in points[:4]]
                    y_coords = [int(p[1]) for p in points[:4]]
                    x = min(x_coords)
                    y = min(y_coords)
                    w = max(x_coords) - x
                    h = max(y_coords) - y
                    qr_boxes.append((x, y, w, h))
        elif isinstance(points, (list, tuple)):
            # Если это список/кортеж
            for point_set in points:
                if point_set is not None:
                    try:
                        if isinstance(point_set, np.ndarray):
                            if len(point_set.shape) == 2 and point_set.shape[0] == 4:
                                x_coords = [int(p[0]) for p in point_set]
                                y_coords = [int(p[1]) for p in point_set]
                                x = min(x_coords)
                                y = min(y_coords)
                                w = max(x_coords) - x
                                h = max(y_coords) - y
                                qr_boxes.append((x, y, w, h))
                        elif len(point_set) == 4:
                            x_coords = [int(p[0]) for p in point_set]
                            y_coords = [int(p[1]) for p in point_set]
                            x = min(x_coords)
                            y = min(y_coords)
                            w = max(x_coords) - x
                            h = max(y_coords) - y
                            qr_boxes.append((x, y, w, h))
                    except (TypeError, IndexError, AttributeError):
                        continue
    
    # Если не нашли, пробуем с улучшенной предобработкой
    if not qr_boxes:
        # CLAHE для улучшения контраста
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_enhanced = clahe.apply(gray)
        retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(gray_enhanced)
        
        if retval and points is not None:
            # Обрабатываем так же, как в первом случае
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
                elif len(points.shape) == 2 and len(points) >= 4:
                    x_coords = [int(p[0]) for p in points[:4]]
                    y_coords = [int(p[1]) for p in points[:4]]
                    x = min(x_coords)
                    y = min(y_coords)
                    w = max(x_coords) - x
                    h = max(y_coords) - y
                    qr_boxes.append((x, y, w, h))
    
    # Если все еще не нашли, пробуем с бинаризацией
    if not qr_boxes:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(binary)
        
        if retval and points is not None:
            # Обрабатываем так же
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
                elif len(points.shape) == 2 and len(points) >= 4:
                    x_coords = [int(p[0]) for p in points[:4]]
                    y_coords = [int(p[1]) for p in points[:4]]
                    x = min(x_coords)
                    y = min(y_coords)
                    w = max(x_coords) - x
                    h = max(y_coords) - y
                    qr_boxes.append((x, y, w, h))
    
    # Удаляем дубликаты (если один QR найден несколькими методами)
    if len(qr_boxes) > 1:
        # Простая проверка на перекрытие
        unique_boxes = []
        for box in qr_boxes:
            is_duplicate = False
            x1, y1, w1, h1 = box
            for existing_box in unique_boxes:
                x2, y2, w2, h2 = existing_box
                # Проверяем перекрытие
                overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
                overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
                overlap_area = overlap_x * overlap_y
                area1 = w1 * h1
                area2 = w2 * h2
                if overlap_area > 0.5 * min(area1, area2):  # 50% перекрытие
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_boxes.append(box)
        qr_boxes = unique_boxes
    
    return qr_boxes


def detect_cells_from_qr(
    image_bgr: np.ndarray,
    qr_box: Tuple[int, int, int, int],
    auto_calibrate: bool = True
) -> Optional[List[Tuple[int, int, int, int]]]:
    """
    Детектирует 11 клеток СНИЛС относительно QR-кода.
    
    Args:
        image_bgr: изображение в формате BGR
        qr_box: bbox QR-кода (x, y, w, h)
        auto_calibrate: использовать авто-калибровку
        
    Returns:
        Список из 11 bbox клеток или None
    """
    qr_x, qr_y, qr_w, qr_h = qr_box
    qr_size = max(qr_w, qr_h)  # Размер QR-кода
    
    # Дефолтные коэффициенты (подобраны эмпирически)
    # СНИЛС обычно справа от QR и чуть ниже
    default_cell_size_ratio = 0.35  # размер клетки относительно QR
    default_gap_ratio = 0.08  # промежуток между клетками
    default_offset_x_ratio = 1.2  # смещение по X (справа от QR)
    default_offset_y_ratio = 0.1  # смещение по Y (чуть ниже)
    
    # Вычисляем предполагаемую область клеток
    cell_size = int(qr_size * default_cell_size_ratio)
    gap = int(qr_size * default_gap_ratio)
    offset_x = int(qr_size * default_offset_x_ratio)
    offset_y = int(qr_size * default_offset_y_ratio)
    
    # Начальная позиция первой клетки (справа от QR, чуть ниже центра)
    start_x = qr_x + qr_w + offset_x
    start_y = qr_y + offset_y
    
    # Если авто-калибровка включена, пытаемся уточнить параметры
    if auto_calibrate:
        # ROI для поиска клеток
        roi_x = start_x - cell_size
        roi_y = start_y - cell_size
        roi_w = cell_size * 15  # достаточно места для 11 клеток + запас
        roi_h = cell_size * 3
        
        # Проверяем границы
        img_h, img_w = image_bgr.shape[:2]
        roi_x = max(0, min(roi_x, img_w - 1))
        roi_y = max(0, min(roi_y, img_h - 1))
        roi_w = min(roi_w, img_w - roi_x)
        roi_h = min(roi_h, img_h - roi_y)
        
        if roi_w > 0 and roi_h > 0:
            roi = image_bgr[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Ищем контуры клеток в ROI
            _, thresh_roi = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Фильтруем контуры по размеру и форме
            cells_in_roi = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < (cell_size * 0.3) ** 2 or area > (cell_size * 1.5) ** 2:
                    continue
                
                # Проверяем прямоугольность
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                if len(approx) != 4:
                    continue
                
                x, y, w_box, h_box = cv2.boundingRect(contour)
                aspect = w_box / h_box if h_box > 0 else 0
                if aspect < 0.7 or aspect > 1.3:
                    continue
                
                cells_in_roi.append((x + roi_x, y + roi_y, w_box, h_box))
            
            # Если нашли клетки, уточняем параметры
            if len(cells_in_roi) >= 5:
                # Сортируем по X
                cells_in_roi.sort(key=lambda c: c[0])
                # Вычисляем средний размер и промежуток
                sizes = [w * h for x, y, w, h in cells_in_roi[:11]]
                if sizes:
                    avg_size = np.mean(sizes)
                    cell_size = int(np.sqrt(avg_size))
                
                gaps = []
                for i in range(len(cells_in_roi) - 1):
                    x1, _, w1, _ = cells_in_roi[i]
                    x2, _, _, _ = cells_in_roi[i + 1]
                    gaps.append(x2 - (x1 + w1))
                if gaps:
                    gap = int(np.mean(gaps))
                
                # Обновляем стартовую позицию
                if cells_in_roi:
                    start_x, start_y, _, _ = cells_in_roi[0]
    
    # Генерируем 11 клеток
    cells = []
    img_h, img_w = image_bgr.shape[:2]
    
    for i in range(11):
        cell_x = start_x + i * (cell_size + gap)
        cell_y = start_y
        
        # Проверяем границы
        if cell_x < 0 or cell_y < 0 or cell_x + cell_size > img_w or cell_y + cell_size > img_h:
            return None  # Выходим за границы
        
        cells.append((cell_x, cell_y, cell_size, cell_size))
    
    return cells


def detect_cells_by_contours(image_bgr: np.ndarray) -> List[List[Tuple[int, int, int, int]]]:
    """
    Fallback детектор: поиск клеток по контурам.
    Улучшенная версия оригинального детектора.
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        Список строк; каждая строка = 11 bbox (x, y, w, h)
    """
    gray, binary, _ = preprocess_for_detection(image_bgr)
    
    # Дополнительная морфология для тонких линий
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.dilate(binary, kernel_dilate, iterations=1)
    
    # Находим контуры
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Фильтруем контуры
    h, w = gray.shape
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
        if aspect < 0.7 or aspect > 1.3:
            continue
        
        # Проверяем заполненность (отношение площади контура к площади bbox)
        bbox_area = w_box * h_box
        if bbox_area > 0:
            fill_ratio = area / bbox_area
            if fill_ratio < 0.3:  # Слишком пустая
                continue
        
        cells.append((x, y, w_box, h_box))
    
    if len(cells) < 11:
        return []
    
    # Группируем по строкам
    cells_with_y = [(x, y, w_box, h_box, y + h_box // 2) for x, y, w_box, h_box in cells]
    cells_with_y.sort(key=lambda c: c[4])
    
    rows = []
    current_row = [cells_with_y[0][:4]]
    current_y = cells_with_y[0][4]
    y_tolerance = h * 0.02
    
    for cell in cells_with_y[1:]:
        x, y, w_box, h_box, y_center = cell
        if abs(y_center - current_y) <= y_tolerance:
            current_row.append((x, y, w_box, h_box))
        else:
            if len(current_row) >= 11:
                rows.append(current_row)
            current_row = [(x, y, w_box, h_box)]
            current_y = y_center
    
    if len(current_row) >= 11:
        rows.append(current_row)
    
    # Ищем последовательности из 11
    result_rows = []
    for row in rows:
        row_sorted = sorted(row, key=lambda c: c[0])
        
        for i in range(len(row_sorted) - 10):
            candidate = row_sorted[i:i+11]
            
            # Проверяем размеры
            sizes = [w * h for x, y, w, h in candidate]
            avg_size = np.mean(sizes)
            size_variance = np.std(sizes) / avg_size if avg_size > 0 else 1
            
            if size_variance > 0.3:
                continue
            
            # Проверяем промежутки
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
            break
    
    return result_rows


def detect_snils_rows(image_bgr: np.ndarray, debug: bool = False) -> Tuple[List[List[Tuple[int, int, int, int]]], Dict[str, Any]]:
    """
    Детектирует строки СНИЛС на изображении.
    Использует двухступенчатый подход: QR-коды (приоритет) + контуры (fallback).
    
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
    image_rotated, angle = deskew(image_bgr)
    debug_info["angle"] = float(angle)
    
    # Предобработка
    gray, binary, preprocess_meta = preprocess_for_detection(image_rotated)
    if debug:
        debug_info["preprocess"] = preprocess_meta
    
    # Шаг 1: Попытка детекции по QR-кодам
    qr_boxes = detect_qr_codes(image_rotated)
    debug_info["qr_count"] = len(qr_boxes)
    debug_info["qr_boxes"] = [(int(x), int(y), int(w), int(h)) for x, y, w, h in qr_boxes]
    
    rows = []
    if qr_boxes:
        debug_info["method"] = "qr"
        # Для каждого QR пытаемся найти строку клеток
        for qr_box in qr_boxes:
            cells = detect_cells_from_qr(image_rotated, qr_box, auto_calibrate=True)
            if cells and len(cells) == 11:
                rows.append(cells)
    
    # Шаг 2: Fallback на контурный детектор
    if not rows:
        debug_info["method"] = "contours"
        rows = detect_cells_by_contours(image_rotated)
    
    debug_info["rows_count"] = len(rows)
    
    # Добавляем bbox строк (всегда, для использования в debug endpoint)
    debug_info["rows_boxes"] = [
        [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for x, y, w, h in row]
        for row in rows
    ]
    
    return rows, debug_info
