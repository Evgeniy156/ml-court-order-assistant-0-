"""Сервис ML предсказаний"""
from .. schemas import PredictionRequest


def calculate_prediction(data: PredictionRequest) -> float:
    """
    Простая эвристика для расчета вероятности успеха судебного приказа. 
    В реальном проекте здесь была бы ML модель. 
    """
    score = 0.5

    # Сумма долга влияет на вероятность
    if 0 < data.total_debt <= 100000:
        score += 0.2
    elif data.total_debt > 100000:
        score -= 0.1

    # Просрочка
    if data.days_overdue > 90:
        score += 0.1

    # Физлицо
    if data. is_physical_person:
        score += 0.05

    # Доля оплаченного
    score -= data.payments_ratio * 0.2

    return max(0.0, min(1.0, score))