# storage/db.py
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


# строка подключения к Postgres из docker-compose
# можно переопределить через переменную окружения DATABASE_URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/ml_court",
)


# движок SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    echo=False,  # если захочешь видеть SQL — поставь True
)

# фабрика сессий
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
