from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


# ЧИСТАЯ строка подключения
DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/ml_court"

print("USING DATABASE_URL:", repr(DATABASE_URL))


engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
