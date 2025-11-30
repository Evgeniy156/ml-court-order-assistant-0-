import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Настройка логирования
logger = logging.getLogger(__name__)

# Получаем `DATABASE_URL` из окружения, иначе SQLite по умолчанию
DATABASE_URL = os.environ.get(
    "DATABASE_URL",  # переменная окружения
    "sqlite:///./dev.db"  # fallback на SQLite, если не указано
)

# SQL echo настраивается через переменную окружения
SQL_ECHO = os.environ.get("SQL_ECHO", "false").lower() in ("true", "1", "yes")

# Для отладки полезно видеть, какая строка подключения используется
logger.info(f"USING DATABASE_URL: '{DATABASE_URL}'")

# Конфигурируем SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    echo=SQL_ECHO,  # Включить дампы SQL в консоль для отладки
    future=True
)

# Базовые модели ORM
class Base(DeclarativeBase):
    pass

# SessionLocal наладка (вызов `SessionLocal()` создаёт сессию)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)