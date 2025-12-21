import os
import re
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _clean_database_url(url: str) -> str:
    """
    Очистка строки подключения от невидимых символов и проблем с кодировкой.
    
    Удаляет:
    - BOM (Byte Order Mark)
    - Неразрывные пробелы (\xa0, \xc2\xa0)
    - Проблемные байты (0xc2 и другие)
    - Другие невидимые символы
    
    Гарантирует, что строка является валидной UTF-8 строкой.
    """
    if not url:
        return url
    
    # Если это не строка, преобразуем
    if not isinstance(url, str):
        try:
            # Пробуем декодировать как UTF-8 с заменой ошибок
            if isinstance(url, bytes):
                url = url.decode('utf-8', errors='replace')
            else:
                url = str(url)
        except (TypeError, UnicodeDecodeError):
            # Если не получается декодировать, пробуем как есть
            url = str(url)
    
    # Убираем BOM если есть
    if url.startswith('\ufeff'):
        url = url[1:]
    
    # Заменяем неразрывные пробелы и проблемные символы
    # \xc2\xa0 - это неразрывный пробел в UTF-8 (два байта)
    # \xa0 - неразрывный пробел в Latin-1
    url = url.replace('\xc2\xa0', ' ')  # Сначала заменяем полный неразрывный пробел
    url = url.replace('\xa0', ' ')       # Затем одиночный
    # Удаляем одиночный байт 0xc2, который может быть проблемой
    # Но только если он не является частью валидной UTF-8 последовательности
    url = url.replace('\xc2', '')
    
    # Удаляем другие невидимые/контрольные символы, но сохраняем все валидные символы URL
    # Удаляем только невидимые Unicode символы (категория Cc, Cf, Zs кроме обычного пробела)
    url = re.sub(r'[\u0000-\u001F\u007F-\u009F\u2000-\u200B\u2028-\u2029\uFEFF]', '', url)
    
    # Убираем пробелы в начале и конце
    url = url.strip()
    
    # Финальная проверка: убеждаемся, что строка валидна UTF-8
    try:
        # Пробуем закодировать и декодировать обратно
        url_bytes = url.encode('utf-8')
        url = url_bytes.decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Если не получается, заменяем проблемные символы
        url = url.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
    return url


# Получаем DATABASE_URL из переменных окружения
_raw_database_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db",
)

# Логируем сырую строку для отладки (только первые 50 символов, без пароля)
if _raw_database_url:
    _debug_url = _raw_database_url[:50] + "..." if len(_raw_database_url) > 50 else _raw_database_url
    logger.debug(f"Raw DATABASE_URL (first 50 chars): {_debug_url}")
    # Проверяем наличие проблемных байтов
    try:
        _raw_database_url.encode('utf-8')
    except UnicodeEncodeError:
        logger.warning("Raw DATABASE_URL contains invalid UTF-8 characters, will be cleaned")
    # Проверяем наличие байта 0xc2
    if '\xc2' in _raw_database_url:
        logger.warning("Raw DATABASE_URL contains \\xc2 byte, will be cleaned")

# Очищаем строку подключения от проблемных символов
DATABASE_URL = _clean_database_url(_raw_database_url)

# Логируем для отладки (без пароля)
if DATABASE_URL.startswith('postgresql://'):
    # Маскируем пароль в логе
    safe_url = DATABASE_URL.split('@')[0].split('//')[0] + '//***@' + '@'.join(DATABASE_URL.split('@')[1:]) if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Database URL configured: {safe_url}")
else:
    logger.info(f"Database URL configured: {DATABASE_URL}")

# Создаем engine с явным указанием кодировки для PostgreSQL
if DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgresql+psycopg2://'):
    # Для PostgreSQL используем psycopg2 с правильной кодировкой
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,  # Проверка соединения перед использованием
    )
else:
    # Для SQLite и других
    engine = create_engine(
        DATABASE_URL,
        echo=False,
    )

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
