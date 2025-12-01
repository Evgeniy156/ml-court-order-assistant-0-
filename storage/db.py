import os
from sqlalchemy import create_engine
from sqlalchemy. orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os. getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db",
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
