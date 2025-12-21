"""
Beam-search декодирование с проверкой checksum СНИЛС.
"""
import numpy as np
from typing import List, Dict, Any, Tuple
from ...utils.snils_checksum import snils_checksum_ok


def beam_search_decode(
    per_cell_topk: List[List[Dict[str, Any]]],
    beam_width: int = 5
) -> Tuple[str, float, List[List[Dict[str, Any]]]]:
    """
    Beam-search декодирование с учетом checksum.
    
    Args:
        per_cell_topk: список topk результатов для каждой из 11 клеток
        beam_width: ширина луча для beam-search
        
    Returns:
        (best_digits, confidence, per_digit_topk)
    """
    if len(per_cell_topk) != 11:
        raise ValueError(f"Ожидается 11 клеток, получено {len(per_cell_topk)}")
    
    # Инициализация: начинаем с пустого пути
    beam = [("", 1.0)]  # (digits_so_far, probability)
    
    # Построение по позициям
    for pos in range(11):
        new_beam = []
        
        for digits, prob in beam:
            # Для каждого пути в луче пробуем topk кандидатов для текущей позиции
            for candidate in per_cell_topk[pos][:beam_width]:
                digit = candidate["digit"]
                p = candidate["p"]
                new_digits = digits + str(digit)
                new_prob = prob * p
                new_beam.append((new_digits, new_prob))
        
        # Сортируем по вероятности и берем top beam_width
        new_beam.sort(key=lambda x: x[1], reverse=True)
        beam = new_beam[:beam_width]
    
    # Фильтруем по checksum и выбираем лучший
    valid_candidates = []
    for digits, prob in beam:
        if snils_checksum_ok(digits):
            # Вычисляем среднюю вероятность по позициям
            avg_prob = prob ** (1.0 / 11)
            valid_candidates.append((digits, avg_prob))
    
    if valid_candidates:
        # Сортируем по вероятности
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        best_digits, confidence = valid_candidates[0]
    else:
        # Если нет валидных, берем лучший по вероятности (без checksum)
        beam.sort(key=lambda x: x[1], reverse=True)
        best_digits = beam[0][0]
        confidence = (beam[0][1]) ** (1.0 / 11)
    
    # Формируем per_digit_topk (используем исходные topk)
    per_digit_topk = per_cell_topk
    
    return best_digits, confidence, per_digit_topk


def decode_row(
    per_cell_topk: List[List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Декодирует строку из 11 клеток с использованием beam-search и checksum.
    
    Args:
        per_cell_topk: список topk результатов для каждой из 11 клеток
        
    Returns:
        Словарь с результатами:
        - digits11: строка из 11 цифр
        - confidence: уверенность (средняя вероятность)
        - is_valid_checksum: прошла ли проверка checksum
        - per_digit: topk для каждой позиции
    """
    # Beam-search декодирование
    digits11, confidence, per_digit_topk = beam_search_decode(per_cell_topk, beam_width=5)
    
    # Проверка checksum
    is_valid = snils_checksum_ok(digits11)
    
    # Если checksum не проходит, пытаемся исправить
    if not is_valid:
        # Находим позиции с низкой уверенностью
        weak_positions = []
        for i, topk_list in enumerate(per_cell_topk):
            if len(topk_list) > 0:
                top1_prob = topk_list[0]["p"]
                weak_positions.append((top1_prob, i))
        
        weak_positions.sort(key=lambda x: x[0])
        weak_positions = [idx for _, idx in weak_positions[:3]]  # Топ-3 слабых
        
        # Перебираем альтернативы для слабых позиций
        best_candidate = digits11
        best_confidence = confidence
        
        def try_corrections(pos_idx, current_digits, current_conf):
            if pos_idx >= len(weak_positions):
                # Проверяем checksum
                if snils_checksum_ok(current_digits):
                    return current_digits, current_conf
                return None, None
            
            pos = weak_positions[pos_idx]
            best_d = None
            best_c = None
            
            # Пробуем top-2 кандидата для этой позиции
            for candidate in per_cell_topk[pos][:2]:
                new_digits = list(current_digits)
                new_digits[pos] = str(candidate["digit"])
                new_digits_str = "".join(new_digits)
                
                # Пересчитываем confidence
                new_probs = []
                for i in range(11):
                    if i == pos:
                        new_probs.append(candidate["p"])
                    else:
                        # Находим вероятность текущей цифры
                        digit = int(new_digits_str[i])
                        found = False
                        for item in per_cell_topk[i]:
                            if item["digit"] == digit:
                                new_probs.append(item["p"])
                                found = True
                                break
                        if not found:
                            new_probs.append(0.5)  # Fallback
                
                new_conf = np.mean(new_probs)
                
                # Рекурсивно пробуем следующую позицию
                d, c = try_corrections(pos_idx + 1, new_digits_str, new_conf)
                if d is not None and (best_d is None or c > best_c):
                    best_d = d
                    best_c = c
            
            return best_d, best_c
        
        corrected_digits, corrected_conf = try_corrections(0, digits11, confidence)
        if corrected_digits is not None:
            digits11 = corrected_digits
            confidence = corrected_conf
            is_valid = True
    
    return {
        "digits11": digits11,
        "confidence": float(confidence),
        "is_valid_checksum": is_valid,
        "per_digit": per_digit_topk
    }

