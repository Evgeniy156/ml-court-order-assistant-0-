import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Получаем `DATABASE_URL` из окружения, иначе SQLite по умолчанию
DATABASE_URL = os.environ.get(
    "DATABASE_URL",  # переменная окружения
    "sqlite:///./dev.db"  # fallback на SQLite, если не указано
)

# Для отладки полезно видеть, какая строка подключения используется
print(f"USING DATABASE_URL: '{DATABASE_URL}'")

# Конфигурируем SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Включить дампы SQL в консоль для отладки
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
