from .db import Base, engine, SessionLocal
from .repository import (
    create_user,
    deposit_credits,
    create_default_ml_models,
)


def init_db() -> None:
    # создаём таблицы, если их ещё нет
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # демо админ
        admin = create_user(
            db,
            email="admin@example.com",
            password="admin123",
            role="admin",
        )

        # демо пользователь
        user = create_user(
            db,
            email="user@example.com",
            password="user123",
            role="user",
        )

        # пополнение баланса демо-пользователя
        deposit_credits(
            db,
            user_id=user.id,
            amount=100,
            description="Initial topup for demo user",
        )

        # базовые ML модели
        create_default_ml_models(db)

        print("DB initialized successfully")
        print(f"Admin id={admin.id}, email={admin.email}")
        print(f"User id={user.id}, email={user.email}")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
