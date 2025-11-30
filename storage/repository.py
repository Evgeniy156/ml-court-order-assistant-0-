from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from .models import UserDB, BillingAccountDB, TransactionDB, MLModelDB


def create_user(
    db: Session,
    email: str,
    password: str,
    role: str = "user",
) -> UserDB:
    """Создать пользователя и связанный billing_account с балансом 0."""
    hashed = bcrypt.hash(password)
    user = UserDB(email=email, hashed_password=hashed, role=role)
    db.add(user)
    db.flush()

    account = BillingAccountDB(user_id=user.id, balance=0)
    db.add(account)

    db.commit()
    db.refresh(user)
    db.refresh(account)
    return user


def get_user_by_email(db: Session, email: str) -> UserDB | None:
    return db.query(UserDB).filter(UserDB.email == email).first()


def deposit_credits(
    db: Session,
    user_id: int,
    amount: float,
    description: str | None = None,
) -> TransactionDB:
    """Пополнение баланса (amount > 0)."""
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    account = (
        db.query(BillingAccountDB)
        .filter(BillingAccountDB.user_id == user_id)
        .first()
    )
    if account is None:
        raise ValueError(f"Счёт пользователя {user_id} не найден")

    account.balance = float(account.balance) + amount

    tx = TransactionDB(
        account_id=account.id,
        amount=amount,
        type="deposit",
        description=description,
    )
    db.add(tx)

    db.commit()
    db.refresh(account)
    db.refresh(tx)
    return tx


def withdraw_credits(
    db: Session,
    user_id: int,
    amount: float,
    description: str | None = None,
) -> TransactionDB:
    """Списание кредитов (amount > 0)."""
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    account = (
        db.query(BillingAccountDB)
        .filter(BillingAccountDB.user_id == user_id)
        .first()
    )
    if account is None:
        raise ValueError(f"Счёт пользователя {user_id} не найден")

    if float(account.balance) < amount:
        raise ValueError("Недостаточно кредитов на балансе")

    account.balance = float(account.balance) - amount

    tx = TransactionDB(
        account_id=account.id,
        amount=-amount,
        type="withdraw",
        description=description,
    )
    db.add(tx)

    db.commit()
    db.refresh(account)
    db.refresh(tx)
    return tx


def get_user_transactions(db: Session, user_id: int) -> list[TransactionDB]:
    """История транзакций пользователя (по убыванию времени)."""
    return (
        db.query(TransactionDB)
        .join(BillingAccountDB, TransactionDB.account_id == BillingAccountDB.id)
        .filter(BillingAccountDB.user_id == user_id)
        .order_by(TransactionDB.created_at.desc())
        .all()
    )


def create_default_ml_models(db: Session) -> None:
    """Создать базовые ML-модели, если ещё не созданы."""
    if db.query(MLModelDB).count() > 0:
        return

    models = [
        MLModelDB(
            name="court_order_suitability_v1",
            description="Модель пригодности дела для судебного приказа",
            price_credits=5,
        ),
        MLModelDB(
            name="debt_risk_scorer_v1",
            description="Риск непогашения задолженности",
            price_credits=3,
        ),
    ]
    db.add_all(models)
    db.commit()
