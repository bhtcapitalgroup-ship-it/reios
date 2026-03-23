import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID_TYPE, JSON_TYPE


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["PortfolioProperty"]] = relationship(back_populates="portfolio")


class PortfolioProperty(Base):
    __tablename__ = "portfolio_properties"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("portfolios.id"), nullable=False)
    property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("properties.id"), nullable=False)
    acquisition_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    acquisition_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    acquisition_costs: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    current_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    valuation_date: Mapped[datetime | None] = mapped_column(DateTime)
    valuation_source: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="active")
    disposition_date: Mapped[datetime | None] = mapped_column(Date)
    disposition_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    disposition_costs: Mapped[float | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    property: Mapped["Property"] = relationship()
    loans: Mapped[list["Loan"]] = relationship(back_populates="portfolio_property")
    income_records: Mapped[list["IncomeRecord"]] = relationship(back_populates="portfolio_property")
    expense_records: Mapped[list["ExpenseRecord"]] = relationship(back_populates="portfolio_property")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("portfolio_properties.id"), nullable=False)
    lender_name: Mapped[str | None] = mapped_column(String(255))
    loan_type: Mapped[str] = mapped_column(String(50), default="conventional")
    original_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    current_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False)
    is_adjustable: Mapped[bool] = mapped_column(Boolean, default=False)
    arm_details: Mapped[dict | None] = mapped_column(JSON_TYPE)
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    amortization_months: Mapped[int | None] = mapped_column(Integer)
    monthly_payment: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    escrow_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    origination_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolio_property: Mapped[PortfolioProperty] = relationship(back_populates="loans")


class IncomeRecord(Base):
    __tablename__ = "income_records"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("portfolio_properties.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), default="rent")
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    paid_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    payment_method: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolio_property: Mapped[PortfolioProperty] = relationship(back_populates="income_records")


class ExpenseRecord(Base):
    __tablename__ = "expense_records"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("portfolio_properties.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    receipt_url: Mapped[str | None] = mapped_column(String(500))
    tax_deductible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolio_property: Mapped[PortfolioProperty] = relationship(back_populates="expense_records")
