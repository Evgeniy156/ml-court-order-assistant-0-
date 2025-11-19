from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional, List, Protocol


# ======================================
#              РОЛИ
# ======================================

class Role(Enum):
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"


# ======================================
#             ПОЛЬЗОВАТЕЛИ
# ======================================

@dataclass
class User:
    id: int
    email: str
    _password_hash: str
    role: Role = Role.USER
    _balance_credits: int = 0

    # --- безопасная работа с паролем ---

    def check_password(self, raw_password: str) -> bool:
        return hash(raw_password) == hash(self._password_hash)

    # --- инкапсуляция баланса через property ---

    @property
    def balance(self) -> int:
        return self._balance_credits

    def can_spend(self, amount: int) -> bool:
        return self._balance_credits >= amount

    def spend(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        if not self.can_spend(amount):
            raise ValueError("Недостаточно средств")
        self._balance_credits -= amount

    def top_up(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        self._balance_credits += amount

    # --- полиморфные методы прав ---

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

    def approve_topup(self, request: "TopUpRequest") -> None:
        request.approve(self)


@dataclass
class Manager(User):
    def __post_init__(self):
        self.role = Role.MANAGER

    def can_view_all_cases(self) -> bool:
        return True


# ======================================
#            ТРАНЗАКЦИИ
# ======================================

class TransactionType(Enum):
    TOP_UP = "top_up"
    SPEND = "spend"


@dataclass
class Transaction:
    id: int
    user: User
    type: TransactionType
    amount: int
    created_at: datetime
    description: str = ""


@dataclass
class TopUpRequest:
    id: int
    user: User
    amount: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[Admin] = None
    approved_at: Optional[datetime] = None

    def is_approved(self) -> bool:
        return self.approved_by is not None

    def approve(self, admin: Admin) -> None:
        if self.is_approved():
            raise ValueError("Уже одобрено")
        self.approved_by = admin
        self.approved_at = datetime.utcnow()
        self.user.top_up(self.amount)


# ======================================
#          МОДЕЛИ ML И ЗАДАЧИ
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
        return 0.8  # заглушка


class MLTaskStatus(Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    FAILED = "failed"
    DONE = "done"


@dataclass
class MLTask:
    id: int
    user: User
    model: MLModel
    created_at: datetime
    input_payload: Any
    status: MLTaskStatus = MLTaskStatus.PENDING
    output: Optional[Any] = None
    error_message: Optional[str] = None
    credits_charged: int = 0

    def start(self):
        if self.status != MLTaskStatus.PENDING:
            raise ValueError("Можно запускать только из PENDING")
        self.status = MLTaskStatus.RUNNING

    def fail(self, message: str):
        self.status = MLTaskStatus.FAILED
        self.error_message = message

    def complete_with_result(self, result: Any, charged: int):
        self.status = MLTaskStatus.DONE
        self.output = result
        self.credits_charged = charged


# ======================================
#      ДОМЕН СУДЕБНОГО ПРИКАЗА
# ======================================

class DebtCaseStatus(Enum):
    DRAFT = "draft"
    PRETRIAL = "pretrial"
    READY_FOR_COURT = "ready_for_court"
    AT_COURT = "at_court"
    COURT_ORDER_ISSUED = "court_order_issued"
    ENFORCEMENT = "enforcement"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class DebtCase:
    id: int
    owner: User
    debtor_full_name: str
    address: str
    account_number: str
    total_debt: float
    penalty_amount: float
    period_from: date
    period_to: date
    status: DebtCaseStatus = DebtCaseStatus.DRAFT

    calculation: Optional["Calculation"] = None
    pretrial_notice: Optional["PretrialNotice"] = None
    court_order: Optional["CourtOrder"] = None
    enforcement: Optional["Enforcement"] = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_eligible_for_court_order(self) -> bool:
        if self.total_debt <= 0:
            return False
        if self.total_debt > 100_000:
            return False
        return True


@dataclass
class CalculationItem:
    period: date
    charged: float
    paid: float
    days_overdue: int
    penalty: float


@dataclass
class Calculation:
    id: int
    debt_case: DebtCase
    items: List[CalculationItem]
    total_debt: float
    total_penalty: float
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PretrialNotice:
    id: int
    debt_case: DebtCase
    sent_at: Optional[date] = None
    delivered_at: Optional[date] = None
    tracking_number: Optional[str] = None
    template_name: str = "default_pretrial_notice"
    file_path: Optional[str] = None

    def mark_sent(self, sent_at: date, tracking_number: str):
        self.sent_at = sent_at
        self.tracking_number = tracking_number

    def mark_delivered(self, delivered_at: date):
        self.delivered_at = delivered_at


@dataclass
class CourtOrder:
    id: int
    debt_case: DebtCase
    court_name: str
    filed_at: Optional[date] = None
    incoming_number: Optional[str] = None
    issued_at: Optional[date] = None
    objections_present: bool = False

    claim_file_path: Optional[str] = None
    order_file_path: Optional[str] = None

    def mark_filed(self, filed_at: date, incoming_number: str):
        self.filed_at = filed_at
        self.incoming_number = incoming_number
        self.debt_case.status = DebtCaseStatus.AT_COURT

    def mark_issued(self, issued_at: date):
        self.issued_at = issued_at
        self.debt_case.status = DebtCaseStatus.COURT_ORDER_ISSUED

    def mark_cancelled_by_objections(self):
        self.objections_present = True
        self.debt_case.status = DebtCaseStatus.CANCELLED


@dataclass
class Enforcement:
    id: int
    debt_case: DebtCase
    sent_to_bailiff_at: Optional[date] = None
    confirmation_file_path: Optional[str] = None

    def mark_sent(self, sent_at: date, confirmation_file_path: str):
        self.sent_to_bailiff_at = sent_at
        self.confirmation_file_path = confirmation_file_path
        self.debt_case.status = DebtCaseStatus.ENFORCEMENT


@dataclass
class DebtCaseFeatures:
    total_debt: float
    penalty_amount: float
    days_overdue: int
    payments_ratio: float
    is_physical_person: bool
