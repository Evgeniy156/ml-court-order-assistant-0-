"""
Multi-pass preprocessing для улучшения качества изображения.
"""
import cv2
import numpy as np
from typing import List, Tuple


def preprocess_multi_pass(image_bgr: np.ndarray) -> List[Tuple[np.ndarray, str]]:
    """
    Применяет несколько вариантов предобработки для перебора.
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        Список кортежей (обработанное_изображение, описание_метода)
    """
    results = []
    h, w = image_bgr.shape[:2]
    
    # Нормализация размера: приводим к ширине 1500px
    target_width = 1500
    if w > 2000:
        scale = target_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        image_bgr = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Pass 1: Grayscale + CLAHE + Adaptive threshold
    gray1 = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    clahe1 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray1 = clahe1.apply(gray1)
    blurred1 = cv2.bilateralFilter(gray1, 9, 75, 75)
    binary1 = cv2.adaptiveThreshold(
        blurred1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    results.append((binary1, "clahe_adaptive"))
    
    # Pass 2: CLAHE + Unsharp mask
    gray2 = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    clahe2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray2 = clahe2.apply(gray2)
    # Unsharp mask
    gaussian = cv2.GaussianBlur(gray2, (0, 0), 2.0)
    unsharp = cv2.addWeighted(gray2, 1.5, gaussian, -0.5, 0)
    binary2 = cv2.adaptiveThreshold(
        unsharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    results.append((binary2, "clahe_unsharp"))
    
    # Pass 3: Upscale x1.5 + CLAHE
    scale_factor = 1.5
    upscaled = cv2.resize(image_bgr, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    gray3 = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
    clahe3 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray3 = clahe3.apply(gray3)
    binary3 = cv2.adaptiveThreshold(
        gray3, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    results.append((binary3, "upscale_clahe"))
    
    # Pass 4: OTSU threshold
    gray4 = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    clahe4 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray4 = clahe4.apply(gray4)
    _, binary4 = cv2.threshold(gray4, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    results.append((binary4, "otsu"))
    
    return results


def deskew_image(image_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
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
            median_angle = np.median(angles)
            if abs(median_angle) > 2:
                h, w = image_bgr.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(
                    image_bgr, M, (w, h), 
                    flags=cv2.INTER_CUBIC, 
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated, float(median_angle)
    
    return image_bgr, 0.0

