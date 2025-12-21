"""
Основной pipeline распознавания СНИЛС.
Объединяет все модули: preprocessing -> detection -> cutting -> recognition -> decoding.
"""
import os
import io
import numpy as np
from PIL import Image
import cv2
from typing import Dict, Any, List
from fastapi import HTTPException, status

from .grid_detect import detect_snils_rows
from .cut_cells import cut_row_cells
from .digit_model import predict_proba, get_model
from .decode import decode_row
from ...utils.snils_checksum import format_snils


ALLOW_PII_OUTPUT = os.getenv("ALLOW_PII_OUTPUT", "false").lower() == "true"


def _check_image_quality(image_bgr: np.ndarray) -> tuple[bool, str]:
    """
    Проверяет качество изображения (резкость, контраст).
    
    Args:
        image_bgr: изображение в формате BGR
        
    Returns:
        (is_ok, warning_message)
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # Проверка резкости через Laplacian variance
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 100:
        return False, "image_too_blurry"
    
    # Проверка контраста
    std_dev = np.std(gray)
    if std_dev < 30:
        return False, "image_too_dark_or_low_contrast"
    
    return True, ""


def _mask_snils(digits: str) -> str:
    """Маскирует СНИЛС, оставляя только первые 3 и последние 2 цифры"""
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}******{digits[9:11]}"


def run_snils_pipeline(image_bytes: bytes, debug: bool = False) -> Dict[str, Any]:
    """
    Основной пайплайн распознавания СНИЛС.
    
    Args:
        image_bytes: байты изображения (JPG/PNG)
        debug: включить debug информацию
        
    Returns:
        Словарь с результатами:
        {
            "count": N,
            "results": [
                {
                    "snils_digits_masked": "000******00",
                    "snils_formatted_masked": "000-***-*** 00",
                    "is_valid_checksum": true,
                    "confidence": 0.87,
                    "warnings": [],
                    "per_digit": [...]
                }
            ],
            "warnings": []
        }
    """
    warnings = []
    debug_info = {}
    
    # Проверяем наличие модели (должна быть загружена заранее)
    try:
        get_model()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="weights not found"
        )
    
    # Декодируем изображение
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        image_rgb = np.array(pil_image)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    except Exception as e:
        return {
            "count": 0,
            "results": [],
            "warnings": [f"Ошибка декодирования изображения: {str(e)}"]
        }
    
    # Проверка качества изображения
    is_ok, quality_warning = _check_image_quality(image_bgr)
    if not is_ok:
        warnings.append(quality_warning)
        if quality_warning == "image_too_blurry":
            return {
                "count": 0,
                "results": [],
                "warnings": ["Изображение слишком размыто. Сделайте более четкое фото."]
            }
        elif quality_warning == "image_too_dark_or_low_contrast":
            return {
                "count": 0,
                "results": [],
                "warnings": ["Изображение слишком темное или низкий контраст. Улучшите освещение."]
            }
    
    # Детектируем строки
    rows, detector_debug = detect_snils_rows(image_bgr, debug=debug)
    debug_info.update(detector_debug)
    
    if not rows:
        error_msg = "Не найдено строк СНИЛС на изображении."
        if detector_debug.get("qr_count", 0) == 0:
            warnings.append("qr_not_found")
        else:
            warnings.append("cells_not_detected")
        
        result = {
            "count": 0,
            "results": [],
            "warnings": [error_msg] + warnings
        }
        if debug:
            result["debug"] = debug_info
        return result
    
    # Распознаем каждую строку
    results = []
    for row_idx, row_cells in enumerate(rows):
        try:
            # Нарезаем и нормализуем клетки
            normalized_cells = cut_row_cells(row_cells, image_bgr)
            
            # Распознаем цифры
            per_cell_topk = predict_proba(normalized_cells, topk=3)
            
            # Декодируем с beam-search и checksum
            decode_result = decode_row(per_cell_topk)
            
            digits11 = decode_result["digits11"]
            confidence = decode_result["confidence"]
            is_valid = decode_result["is_valid_checksum"]
            per_digit_topk = decode_result["per_digit"]
            
            # Формируем предупреждения
            row_warnings = []
            if not is_valid:
                row_warnings.append("Контрольная сумма не прошла проверку")
            if confidence < 0.5:
                row_warnings.append("Низкая уверенность распознавания")
            
            # Маскируем СНИЛС
            if ALLOW_PII_OUTPUT:
                snils_digits = digits11
                snils_formatted = format_snils(digits11)
            else:
                snils_digits = _mask_snils(digits11)
                snils_formatted = format_snils(_mask_snils(digits11))
            
            result = {
                "snils_digits_masked": snils_digits,
                "snils_formatted_masked": snils_formatted,
                "is_valid_checksum": is_valid,
                "confidence": confidence,
                "warnings": row_warnings,
                "per_digit": [
                    {"digit": item["digit"], "p": item["p"]}
                    for item in per_digit_topk
                ]
            }
            
            results.append(result)
            
        except Exception as e:
            warnings.append(f"Ошибка при распознавании строки {row_idx + 1}: {str(e)}")
    
    result = {
        "count": len(results),
        "results": results,
        "warnings": warnings
    }
    
    if debug:
        result["debug"] = debug_info
    
    return result

