"""
Пайплайн распознавания СНИЛС.
Объединяет детекцию, распознавание и проверку контрольной суммы.
"""
import os
import io
import numpy as np
from PIL import Image
import cv2
from typing import List, Dict, Any, Tuple

from .snils_detector import detect_snils_rows
from .snils_recognizer import recognize_row
from ..utils.snils_checksum import snils_checksum_ok, format_snils


ALLOW_PII_OUTPUT = os.getenv("ALLOW_PII_OUTPUT", "false").lower() == "true"


def _check_image_quality(image_bgr: np.ndarray) -> Tuple[bool, str]:
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
    if laplacian_var < 100:  # Низкая резкость
        return False, "image_too_blurry"
    
    # Проверка контраста через стандартное отклонение
    std_dev = np.std(gray)
    if std_dev < 30:  # Низкий контраст
        return False, "image_too_dark_or_low_contrast"
    
    return True, ""


def _mask_snils(digits: str) -> str:
    """Маскирует СНИЛС, оставляя только первые 3 и последние 2 цифры"""
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}******{digits[9:11]}"


def _autocorrect_snils(
    digits11: str,
    topk_list: List[List[Dict[str, Any]]],
    per_digit_probs: List[float],
) -> tuple[str, float]:
    """
    Пытается исправить СНИЛС, если checksum не проходит.
    
    Выбирает 3 позиции с минимальной уверенностью top1,
    перебирает комбинации top-2 кандидатов для этих позиций.
    
    Args:
        digits11: исходная строка из 11 цифр
        topk_list: список topk результатов для каждой клетки
        per_digit_probs: вероятности top1 для каждой клетки
        
    Returns:
        Кортеж (исправленная строка, новый confidence)
    """
    # Находим 3 позиции с минимальной уверенностью
    prob_with_index = [(per_digit_probs[i], i) for i in range(11)]
    prob_with_index.sort(key=lambda x: x[0])
    weak_positions = [idx for _, idx in prob_with_index[:3]]
    
    # Для каждой слабой позиции берем top-2 кандидата
    candidates_per_pos = []
    for pos in weak_positions:
        if len(topk_list[pos]) >= 2:
            candidates_per_pos.append([
                topk_list[pos][0]["digit"],
                topk_list[pos][1]["digit"]
            ])
        else:
            candidates_per_pos.append([topk_list[pos][0]["digit"]])
    
    # Перебираем комбинации (максимум 8 вариантов: 2^3)
    best_digits = digits11
    best_score = 0.0
    
    def generate_combinations(candidates_list, current_combination, index):
        if index == len(candidates_list):
            # Проверяем эту комбинацию
            test_digits = list(digits11)
            for i, pos in enumerate(weak_positions):
                test_digits[pos] = str(current_combination[i])
            test_str = "".join(test_digits)
            
            if snils_checksum_ok(test_str):
                # Вычисляем score (средняя вероятность)
                score = 0.0
                for i, pos in enumerate(weak_positions):
                    digit = current_combination[i]
                    # Находим вероятность этого кандидата
                    for item in topk_list[pos]:
                        if item["digit"] == digit:
                            score += item["p"]
                            break
                score /= len(weak_positions)
                
                nonlocal best_digits, best_score
                if score > best_score:
                    best_digits = test_str
                    best_score = score
            return
        
        for candidate in candidates_list[index]:
            generate_combinations(
                candidates_list,
                current_combination + [candidate],
                index + 1
            )
    
    generate_combinations(candidates_per_pos, [], 0)
    
    # Вычисляем новый confidence
    if best_digits != digits11:
        # Пересчитываем confidence для исправленной строки
        new_probs = per_digit_probs.copy()
        for i, pos in enumerate(weak_positions):
            new_digit = int(best_digits[pos])
            # Находим вероятность нового кандидата
            for item in topk_list[pos]:
                if item["digit"] == new_digit:
                    new_probs[pos] = item["p"]
                    break
        new_confidence = np.mean(new_probs)
    else:
        new_confidence = np.mean(per_digit_probs)
    
    return best_digits, new_confidence


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
            "results": [...],
            "warnings": [...],
            "debug": {...}  # только если debug=True
        }
    """
    warnings = []
    debug_info = {}
    
    # Декодируем изображение
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        # Конвертируем в RGB если нужно
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        # Конвертируем в numpy array
        image_rgb = np.array(pil_image)
        # Конвертируем RGB -> BGR для OpenCV
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
    
    # Всегда обновляем debug_info (даже если debug=False, нужна базовая информация)
    debug_info.update(detector_debug)
    
    if not rows:
        # Формируем понятное сообщение об ошибке
        error_msg = "Не найдено строк СНИЛС на изображении."
        if detector_debug.get("qr_count", 0) == 0:
            error_msg += " QR-коды не обнаружены."
            warnings.append("qr_not_found")
        elif detector_debug.get("method") == "qr":
            error_msg += " QR-коды найдены, но клетки не обнаружены."
            warnings.append("cells_not_detected")
        else:
            error_msg += " Клетки не обнаружены контурным методом."
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
            # Распознаем строку
            recognition_result = recognize_row(row_cells, image_bgr)
            digits11 = recognition_result["digits11"]
            topk_list = recognition_result["topk"]
            per_digit_probs = recognition_result["per_digit_probs"]
            
            # Вычисляем confidence (среднее по top1)
            confidence = float(np.mean(per_digit_probs))
            
            # Проверяем checksum
            is_valid = snils_checksum_ok(digits11)
            
            # Если checksum не проходит, пытаемся исправить
            if not is_valid:
                corrected_digits, new_confidence = _autocorrect_snils(
                    digits11, topk_list, per_digit_probs
                )
                if corrected_digits != digits11 and snils_checksum_ok(corrected_digits):
                    digits11 = corrected_digits
                    is_valid = True
                    confidence = new_confidence
                    warnings.append(f"Строка {row_idx + 1}: применена автокоррекция")
            
            # Формируем результат
            row_warnings = []
            if not is_valid:
                row_warnings.append("Контрольная сумма не прошла проверку")
            if confidence < 0.5:
                row_warnings.append("Низкая уверенность распознавания")
            
            # Маскируем СНИЛС (если не разрешен вывод PII)
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
                    {"digit": item.get("digit") if isinstance(item, dict) else item[0], 
                     "p": item.get("p") if isinstance(item, dict) else item[1]}
                    for item in topk_list
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


