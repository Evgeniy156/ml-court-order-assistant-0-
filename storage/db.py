import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


# Берём строку подключения из окружения, по умолчанию — sqlite dev.db
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db",
)

# Движок SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Если хочешь видеть SQL — поставь True
)

# Фабрика сессий
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
<<<<<<< HEAD
    autoflush=False
=======
>>>>>>> 6842a3f (Add working Telegram bot implementation for DZ4)
)
