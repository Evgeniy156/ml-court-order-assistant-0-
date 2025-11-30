import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Получаем DATABASE_URL из окружения, иначе SQLite по умолчанию
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./dev.db"
)

# Конфигурируем SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)
