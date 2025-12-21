"""
Нарезка и нормализация клеток из строк.
"""
import cv2
import numpy as np
from typing import List, Tuple


def normalize_cell(cell_img: np.ndarray, target_size: int = 32) -> np.ndarray:
    """
    Нормализует изображение клетки до фиксированного размера.
    
    Args:
        cell_img: изображение клетки (grayscale или BGR)
        target_size: целевой размер (target_size x target_size)
        
    Returns:
        Нормализованное изображение (grayscale, target_size x target_size)
    """
    # Конвертируем в grayscale если нужно
    if len(cell_img.shape) == 3:
        gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cell_img.copy()
    
    h, w = gray.shape
    
    # Добавляем padding для сохранения пропорций
    pad = max(h, w) // 10
    padded = cv2.copyMakeBorder(gray, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
    
    # Resize до target_size x target_size
    resized = cv2.resize(padded, (target_size, target_size), interpolation=cv2.INTER_AREA)
    
    # Инвертируем если нужно (цифры должны быть белыми на черном)
    # Проверяем, что фон светлее цифр
    mean_val = np.mean(resized)
    if mean_val > 127:
        # Фон светлый, инвертируем
        resized = 255 - resized
    
    return resized


def cut_row_cells(
    row_cells: List[Tuple[int, int, int, int]], 
    image_bgr: np.ndarray
) -> List[np.ndarray]:
    """
    Нарезает и нормализует 11 клеток из строки.
    
    Args:
        row_cells: список bbox (x, y, w, h) для 11 клеток
        image_bgr: исходное изображение в BGR
        
    Returns:
        Список нормализованных изображений клеток (32x32 grayscale)
    """
    if len(row_cells) != 11:
        raise ValueError(f"Ожидается 11 клеток, получено {len(row_cells)}")
    
    normalized_cells = []
    for x, y, w, h in row_cells:
        # Кроп клетки
        cell_img = image_bgr[y:y+h, x:x+w]
        
        # Нормализуем
        normalized = normalize_cell(cell_img, target_size=32)
        normalized_cells.append(normalized)
    
    return normalized_cells

