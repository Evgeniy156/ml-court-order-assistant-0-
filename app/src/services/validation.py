"""Модуль валидации данных"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError, Field, validator


class PredictionDataValidator(BaseModel):
    """Валидатор для данных предсказания"""
    total_debt: float = Field(..., gt=0, description="Сумма задолженности должна быть положительной")
    penalty_amount: float = Field(..., ge=0, description="Сумма пени не может быть отрицательной")
    days_overdue: int = Field(..., ge=0, description="Дней просрочки не может быть отрицательным")
    payments_ratio: float = Field(..., ge=0, le=1, description="Доля оплаченного должна быть от 0 до 1")
    is_physical_person: bool = Field(..., description="Указание физического лица")
    
    @validator('total_debt')
    def validate_total_debt(cls, v):
        if v > 1000000000:  # 1 миллиард
            raise ValueError("Сумма задолженности слишком большая")
        return v
    
    @validator('days_overdue')
    def validate_days_overdue(cls, v):
        if v > 3650:  # 10 лет
            raise ValueError("Количество дней просрочки слишком большое")
        return v


class CSVRowValidator(BaseModel):
    """Валидатор для строки CSV"""
    total_debt: float
    penalty_amount: float
    days_overdue: int
    payments_ratio: float
    is_physical_person: str  # Принимаем строку, потом преобразуем
    
    @validator('total_debt', 'penalty_amount', 'payments_ratio', pre=True)
    def parse_float(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Пустое значение")
        try:
            return float(v)
        except (ValueError, TypeError):
            raise ValueError(f"Некорректное числовое значение: {v}")
    
    @validator('days_overdue', pre=True)
    def parse_int(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Пустое значение")
        try:
            return int(float(v))  # Сначала float, потом int для обработки "10.0"
        except (ValueError, TypeError):
            raise ValueError(f"Некорректное целое значение: {v}")
    
    @validator('is_physical_person', pre=True)
    def parse_bool(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            return v in ('true', '1', 'yes', 'да', 'y')
        return bool(v)
    
    @validator('total_debt')
    def validate_total_debt(cls, v):
        if v <= 0:
            raise ValueError("Сумма задолженности должна быть положительной")
        if v > 1000000000:
            raise ValueError("Сумма задолженности слишком большая")
        return v
    
    @validator('penalty_amount')
    def validate_penalty_amount(cls, v):
        if v < 0:
            raise ValueError("Сумма пени не может быть отрицательной")
        return v
    
    @validator('days_overdue')
    def validate_days_overdue(cls, v):
        if v < 0:
            raise ValueError("Дней просрочки не может быть отрицательным")
        if v > 3650:
            raise ValueError("Количество дней просрочки слишком большое")
        return v
    
    @validator('payments_ratio')
    def validate_payments_ratio(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Доля оплаченного должна быть от 0 до 1")
        return v


def validate_prediction_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидация данных для предсказания
    
    Returns:
        Валидированные данные
        
    Raises:
        ValueError: При ошибке валидации
    """
    try:
        validator = PredictionDataValidator(**data)
        return validator.dict()
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        raise ValueError("; ".join(errors))


def validate_csv_row(row: Dict[str, Any], row_number: int) -> Dict[str, Any]:
    """
    Валидация строки CSV
    
    Args:
        row: Словарь с данными строки
        row_number: Номер строки (для сообщений об ошибках)
        
    Returns:
        Валидированные данные
        
    Raises:
        ValueError: При ошибке валидации
    """
    try:
        validator = CSVRowValidator(**row)
        data = validator.dict()
        # Преобразуем is_physical_person в bool
        data['is_physical_person'] = bool(data['is_physical_person'])
        return data
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        raise ValueError(f"Строка {row_number}: " + "; ".join(errors))
    except Exception as e:
        raise ValueError(f"Строка {row_number}: {str(e)}")


def validate_file_size(file_size: int, max_size_mb: int = 10) -> None:
    """
    Валидация размера файла
    
    Args:
        file_size: Размер файла в байтах
        max_size_mb: Максимальный размер в МБ
        
    Raises:
        ValueError: Если файл слишком большой
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValueError(f"Файл слишком большой. Максимальный размер: {max_size_mb} МБ")


def validate_file_extension(filename: str, allowed_extensions: List[str] = None) -> None:
    """
    Валидация расширения файла
    
    Args:
        filename: Имя файла
        allowed_extensions: Список разрешенных расширений (по умолчанию ['.csv'])
        
    Raises:
        ValueError: Если расширение не разрешено
    """
    if allowed_extensions is None:
        allowed_extensions = ['.csv']
    
    if not filename:
        raise ValueError("Имя файла не может быть пустым")
    
    extension = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    if not extension or f'.{extension}' not in allowed_extensions:
        raise ValueError(f"Разрешенные расширения: {', '.join(allowed_extensions)}")

