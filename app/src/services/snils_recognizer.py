"""
Baseline распознавание цифр без обучения.
Использует шаблоны, сгенерированные с cv2.putText.
"""
import cv2
import numpy as np
from typing import List, Tuple
import os


# Кэш шаблонов
_templates_cache = None


def _generate_templates() -> List[np.ndarray]:
    """
    Генерирует шаблоны цифр 0-9 с разными вариантами scale/thickness.
    
    Returns:
        Список шаблонов, каждый размером 64x64
    """
    templates = []
    size = 64
    
    # Варианты параметров для генерации
    scales = [0.8, 1.0, 1.2]
    thicknesses = [2, 3]
    
    for digit in range(10):
        digit_templates = []
        for scale in scales:
            for thickness in thicknesses:
                img = np.zeros((size, size), dtype=np.uint8)
                text = str(digit)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = scale
                
                # Получаем размер текста для центрирования
                (text_width, text_height), baseline = cv2.getTextSize(
                    text, font, font_scale, thickness
                )
                
                # Центрируем текст
                x = (size - text_width) // 2
                y = (size + text_height) // 2
                
                cv2.putText(
                    img, text, (x, y), font, font_scale, 255, thickness, cv2.LINE_AA
                )
                
                digit_templates.append(img)
        
        # Берем лучший вариант (самый четкий)
        templates.append(digit_templates[0])
    
    return templates


def _get_templates() -> List[np.ndarray]:
    """Получает шаблоны (с кэшированием)"""
    global _templates_cache
    if _templates_cache is None:
        _templates_cache = _generate_templates()
    return _templates_cache


def recognize_cell(cell_img: np.ndarray, topk: int = 3) -> List[Tuple[int, float]]:
    """
    Распознает цифру в клетке.
    
    Args:
        cell_img: изображение клетки (grayscale или BGR)
        topk: количество лучших кандидатов
        
    Returns:
        Список кортежей (digit, probability) отсортированных по убыванию вероятности
    """
    # Если BGR, конвертируем в grayscale
    if len(cell_img.shape) == 3:
        cell_img = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
    
    # Подготовка: pad и resize до 64x64
    h, w = cell_img.shape
    # Добавляем padding
    pad = max(h, w) // 10
    padded = cv2.copyMakeBorder(cell_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
    
    # Resize до 64x64
    resized = cv2.resize(padded, (64, 64), interpolation=cv2.INTER_AREA)
    
    # Binarize (если еще не бинарное)
    _, binary = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Получаем шаблоны
    templates = _get_templates()
    
    # Сравниваем с каждым шаблоном
    scores = []
    for digit, template in enumerate(templates):
        # Используем matchTemplate
        result = cv2.matchTemplate(binary, template, cv2.TM_CCOEFF_NORMED)
        max_val = np.max(result)
        scores.append((digit, float(max_val)))
    
    # Сортируем по убыванию score
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Применяем softmax для получения вероятностей
    exp_scores = np.exp([s[1] for s in scores])
    sum_exp = np.sum(exp_scores)
    probabilities = [exp_scores[i] / sum_exp for i in range(len(scores))]
    
    # Возвращаем topk
    result = [(scores[i][0], probabilities[i]) for i in range(min(topk, len(scores)))]
    
    return result


def recognize_row(cells: List[Tuple[int, int, int, int]], image_bgr: np.ndarray) -> dict:
    """
    Распознает строку из 11 клеток.
    
    Args:
        cells: список bbox (x, y, w, h) для 11 клеток
        image_bgr: исходное изображение в BGR
        
    Returns:
        Словарь с результатами:
        - digits11: строка из 11 цифр (top1 для каждой клетки)
        - topk: список списков (digit, prob) для каждой клетки
        - per_digit_probs: список вероятностей для top1 каждой клетки
    """
    if len(cells) != 11:
        raise ValueError(f"Ожидается 11 клеток, получено {len(cells)}")
    
    digits = []
    topk_list = []
    per_digit_probs = []
    
    for x, y, w, h in cells:
        # Кроп клетки
        cell_img = image_bgr[y:y+h, x:x+w]
        
        # Распознаем
        topk_result = recognize_cell(cell_img, topk=3)
        
        # Top1
        top1_digit, top1_prob = topk_result[0]
        digits.append(str(top1_digit))
        topk_list.append([{"digit": d, "p": p} for d, p in topk_result])
        per_digit_probs.append(top1_prob)
    
    digits11 = "".join(digits)
    
    return {
        "digits11": digits11,
        "topk": topk_list,
        "per_digit_probs": per_digit_probs,
    }

