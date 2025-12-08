#!/usr/bin/env python3
"""
Seed/demo data для ДЗ №3 (SQLAlchemy).
Запуск:
  python .\scripts\seed_db.py
"""
from datetime import datetime
import sys

try:
    from storage.db import engine, Base, SessionLocal
    from storage import models
except Exception as e:
    print("Не удалось импортировать storage.db или storage.models:", e)
    sys.exit(1)


def create_demo_data(session):
    # Создаём demo пользователя и admin, если их нет
    demo = session.query(models.UserDB).filter_by(email="demo@example.com").first()
    admin = session.query(models.UserDB).filter_by(email="admin@example.com").first()

    if demo and admin:
        print("Демо-пользователи уже существуют — пропускаем создание.")
        return

    if not demo:
        demo = models.UserDB(
            email="demo@example.com",
            hashed_password="demo_password_hash",
            role="user",
        )
        session.add(demo)
        session.flush()  # получить id
        demo_account = models.BillingAccountDB(user_id=demo.id, balance=100.0)
        session.add(demo_account)
        print("Создан demo user и billing account")

    if not admin:
        admin = models.UserDB(
            email="admin@example.com",
            hashed_password="admin_password_hash",
            role="admin",
        )
        session.add(admin)
        session.flush()
        admin_account = models.BillingAccountDB(user_id=admin.id, balance=1000.0)
        session.add(admin_account)
        print("Создан demo admin и billing account")

    # Добавляем пару ML-моделей, если модель присутствует
    if hasattr(models, "MLModelDB"):
        exists = session.query(models.MLModelDB).filter_by(name="ocr_basic").first()
        if not exists:
            m1 = models.MLModelDB(name="ocr_basic", description="OCR baseline", price_credits=1)
            m2 = models.MLModelDB(name="ocr_premium", description="OCR improved", price_credits=5)
            session.add_all([m1, m2])
            print("Добавлены demo ML-модели")

    # Добавим начальную транзакцию для demo user (если есть TransactionDB)
    if hasattr(models, "TransactionDB") and demo:
        # получим account
        account = session.query(models.BillingAccountDB).filter_by(user_id=demo.id).first()
        if account:
            tx = models.TransactionDB(
                account_id=account.id,
                amount=100.0,
                type="topup",
                created_at=datetime.utcnow(),
                description="Initial top-up for demo"
            )
            session.add(tx)
            print("Добавлена demo транзакция")


def main():
    print("Проверяем/создаём таблицы...")
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        create_demo_data(session)
        session.commit()
        print("Демо-данные успешно добавлены.")
    except Exception as e:
        session.rollback()
        print("Ошибка при заполнении демо-данных:", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()