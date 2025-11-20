from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional, List, Protocol


# ======================================
#                РОЛИ
# ======================================

class Role(Enum):
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"


# ======================================
#        УПРАВЛЕНИЕ БАЛАНСОМ
# ======================================

@dataclass
class BillingAccount:
    """
    Личный счёт пользователя.
    Баланс — зона ответственности BILLING, а не User.
    """
    account_id: int
    user_id: int
    balance: int = 0

    def deposit(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        self.balance += amount

    def withdraw(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        if self.balance < amount:
            raise ValueError("Недостаточно средств")
        self.balance -= amount


class BillingService:
    """
    Управляющая сущность, которая работает с аккаунтами пользователей.
    """
    def charge(self, account: BillingAccount, amount: int, description: str) -> "Transaction":
        account.withdraw(amount)
        return Transaction(
            id=0,
            user_id=account.user_id,
            type=TransactionType.SPEND,
            amount=amount,
            description=description,
            created_at=datetime.utcnow()
        )

    def add_funds(self, account: BillingAccount, amount: int, description: str) -> "Transaction":
        account.deposit(amount)
        return Transaction(
            id=0,
            user_id=account.user_id,
            type=TransactionType.TOP_UP,
            amount=amount,
            description=description,
            created_at=datetime.utcnow()
        )


# ======================================
#        ПОЛЬЗОВАТЕЛИ И РОЛИ
# ======================================

@dataclass
class User:
    id: int
    email: str
    _password_hash: str
    role: Role = Role.USER

    billing_account: Optional[BillingAccount] = None
    transaction_history: Optional["UserTransactionHistory"] = None
    prediction_history: Optional["UserPredictionHistory"] = None

    def check_password(self, raw_password: str) -> bool:
        return hash(raw_password) == hash(self._password_hash)

    # --- права (полиморфизм) ---

    def can_view_all_cases(self) -> bool:
        return False

    def can_approve_topups(self) -> bool:
        return False


@dataclass
class Admin(User):
    def __post_init__(self):
        self.role = Role.ADMIN

    def can_view_all_cases(self) -> bool:
        return True

    def can_approve_topups(self) -> bool:
        return True


@dataclass
class Manager(User):
    def __post_init__(self):
        self.role = Role.MANAGER

    def can_view_all_cases(self) -> bool:
        return True


# ======================================
#       ИСТОРИЯ ТРАНЗАКЦИЙ
# ======================================

class TransactionType(Enum):
    TOP_UP = "top_up"
    SPEND = "spend"


@dataclass
class Transaction:
    id: int
    user_id: int
    type: TransactionType
    amount: int
    created_at: datetime
    description: str = ""


@dataclass
class UserTransactionHistory:
    """
    История всех транзакций пользователя.
    """
    user_id: int
    transactions: List[Transaction] = field(default_factory=list)

    def add(self, tx: Transaction) -> None:
        self.transactions.append(tx)


# ======================================
#       ML-МОДЕЛИ И ИСТОРИЯ ПРЕДСКАЗАНИЙ
# ======================================

class MLModel(Protocol):
    id: int
    name: str
    price_per_request: int
    def predict(self, payload: Any) -> Any:
        ...


@dataclass
class CourtOrderSuitabilityModel:
    id: int
    name: str
    version: str
    price_per_request: int = 10

    def predict(self, payload: "DebtCaseFeatures") -> float:
        return 0.8


class MLTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    DONE = "done"


@dataclass
class MLTask:
    id: int
    user_id: int
    model: MLModel
    created_at: datetime
    input_payload: Any
    status: MLTaskStatus = MLTaskStatus.PENDING
    output: Optional[Any] = None
    error_message: Optional[str] = None

    credits_charged: int = 0


@dataclass
class UserPredictionHistory:
    """
    История всех ML-задач пользователя.
    """
    user_id: int
    predictions: List[MLTask] = field(default_factory=list)

    def add(self, task: MLTask) -> None:
        self.predictions.append(task)


# ======================================
#            ДОМЕН: ДЕЛА
# ======================================

class DebtCaseStatus(Enum):
    DRAFT = "draft"
    PRETRIAL = "pretrial"
    AT_COURT = "at_court"
    COURT_ORDER_ISSUED = "issued"
    ENFORCEMENT = "enforcement"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class DebtCase:
    id: int
    owner_id: int
    debtor_full_name: str
    address: str
    account_number: str
    total_debt: float
    penalty_amount: float
    period_from: date
    period_to: date
    status: DebtCaseStatus = DebtCaseStatus.DRAFT

    def is_eligible_for_court_order(self) -> bool:
        return 0 < self.total_debt <= 100_000


@dataclass
class DebtCaseFeatures:
    total_debt: float
    penalty_amount: float
    days_overdue: int
    payments_ratio: float
    is_physical_person: bool
