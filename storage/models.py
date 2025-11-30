from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    Numeric,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user")  # user / manager / admin

    # один пользователь → один биллинговый аккаунт
    billing_account: Mapped["BillingAccountDB"] = relationship(
        back_populates="user",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<UserDB id={self.id} email={self.email} role={self.role}>"



class BillingAccountDB(Base):
    __tablename__ = "billing_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    # баланс в кредитах / рублях — как по заданию
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    user: Mapped[UserDB] = relationship(back_populates="billing_account")
    transactions: Mapped[list["TransactionDB"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BillingAccountDB user_id={self.user_id} balance={self.balance}>"



class TransactionDB(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("billing_accounts.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    type: Mapped[str] = mapped_column(String(50))  # deposit / withdraw
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    account: Mapped[BillingAccountDB] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<TransactionDB id={self.id} account_id={self.account_id} "
            f"amount={self.amount} type={self.type} created_at={self.created_at}>"
        )



class MLModelDB(Base):
    """Метаданные ML-модели: имя, сколько кредитов списывает и т.д."""

    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price_credits: Mapped[int] = mapped_column(default=1)

    def __repr__(self) -> str:
        return f"<MLModelDB id={self.id} name={self.name} price={self.price_credits}>"
