#!/usr/bin/env python3
"""
Небольшой скрипт для проверки модели/БД:
- Показывает всех пользователей
- Создаёт тестового пользователя, если он отсутствует
- Создаёт/обновляет BillingAccount и Transaction
Запуск:
  python scripts/check_db.py
"""
from datetime import datetime
import sys

try:
    from storage.db import SessionLocal, engine, Base
    from storage import models
except Exception as e:
    print("Не удалось импортировать storage.db или storage.models:", e)
    sys.exit(1)

def print_users(session):
    users = session.query(models.UserDB).all()
    print(f"Users ({len(users)}):")
    for u in users:
        try:
            print(f" - id={u.id} email={u.email} role={u.role}")
        except Exception:
            print(" - (невозможно распечатать поля пользователя)")

def ensure_demo_user(session):
    u = session.query(models.UserDB).filter_by(email="demo_check@example.com").first()
    if u:
        print("Demo check user already exists:", u.email)
        return u
    u = models.UserDB(email="demo_check@example.com", hashed_password="x", role="user")
    session.add(u)
    session.flush()
    print("Создан demo_check user id=", u.id)
    return u

def ensure_billing_and_tx(session, user):
    account = session.query(models.BillingAccountDB).filter_by(user_id=user.id).first()
    if not account:
        account = models.BillingAccountDB(user_id=user.id, balance=10.0)
        session.add(account)
        session.flush()
        print("Создан billing account id=", account.id, "balance=", account.balance)
    else:
        print("Найден billing account id=", account.id, "balance=", account.balance)

    # Добавим транзакцию - topup 5
    if hasattr(models, "TransactionDB"):
        tx = models.TransactionDB(
            account_id=account.id,
            amount=5.0,
            type="topup",
            created_at=datetime.utcnow(),
            description="Check script topup"
        )
        account.balance = float(account.balance) + 5.0
        session.add(tx)
        session.flush()
        print("Добавлена транзакция id=", getattr(tx, "id", None))
    else:
        print("Модель TransactionDB не найдена. Пропускаем создание транзакции.")

def main():
    # Создаем таблицы, если нужно (idempotent)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        print_users(session)
        user = ensure_demo_user(session)
        ensure_billing_and_tx(session, user)
        session.commit()
        print("Коммит выполнен.")
        print_users(session)
    except Exception as e:
        session.rollback()
        print("Ошибка во время проверки:", e)
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()