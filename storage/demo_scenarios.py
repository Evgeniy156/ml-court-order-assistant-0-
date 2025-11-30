from .db import SessionLocal
from .repository import (
    get_user_by_email,
    deposit_credits,
    withdraw_credits,
    get_user_transactions,
)


def run_demo():
    db = SessionLocal()
    try:
        user = get_user_by_email(db, "user@example.com")
        if user is None:
            raise RuntimeError("Demo user not found. Run storage.init_db first.")

        print(f"User: id={user.id}, email={user.email}, role={user.role}")
        print(f"Initial balance: {user.billing_account.balance}")

        # пополнение
        tx1 = deposit_credits(db, user_id=user.id, amount=25, description="Topup demo")
        print("Deposit transaction:", tx1)

        # списание
        tx2 = withdraw_credits(
            db,
            user_id=user.id,
            amount=10,
            description="Charge for ML prediction",
        )
        print("Withdraw transaction:", tx2)

        db.refresh(user)
        print(f"Final balance: {user.billing_account.balance}")

        # история транзакций
        print("\nTransaction history:")
        for tx in get_user_transactions(db, user.id):
            print(f"- {tx.created_at} [{tx.type}] {tx.amount} ({tx.description})")

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
