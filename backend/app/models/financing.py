import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID_TYPE, JSON_TYPE, ARRAY_TYPE


class Lender(Base):
    __tablename__ = "lenders"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    contact: Mapped[dict | None] = mapped_column(JSON_TYPE)
    website: Mapped[str | None] = mapped_column(String(500))
    geographic_areas: Mapped[list | None] = mapped_column(ARRAY_TYPE)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    commission_structure: Mapped[dict | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    products: Mapped[list["LendingProduct"]] = relationship(back_populates="lender")


class LendingProduct(Base):
    __tablename__ = "lending_products"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    lender_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("lenders.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    loan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    min_credit_score: Mapped[int | None] = mapped_column(Integer)
    max_ltv: Mapped[float | None] = mapped_column(Numeric(5, 2))
    rate_range_low: Mapped[float | None] = mapped_column(Numeric(5, 3))
    rate_range_high: Mapped[float | None] = mapped_column(Numeric(5, 3))
    min_loan_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    max_loan_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    property_types: Mapped[list | None] = mapped_column(ARRAY_TYPE)
    min_dscr: Mapped[float | None] = mapped_column(Numeric(4, 2))
    prepayment_penalty: Mapped[dict | None] = mapped_column(JSON_TYPE)
    requirements: Mapped[dict | None] = mapped_column(JSON_TYPE)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    lender: Mapped[Lender] = relationship(back_populates="products")


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    deal_id: Mapped[str | None] = mapped_column(UUID_TYPE, ForeignKey("deals.id"))
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    borrower_profile: Mapped[dict | None] = mapped_column(JSON_TYPE)
    property_details: Mapped[dict | None] = mapped_column(JSON_TYPE)
    requested_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    documents: Mapped[dict | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    quotes: Mapped[list["LoanQuote"]] = relationship(back_populates="application")


class LoanQuote(Base):
    __tablename__ = "loan_quotes"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("loan_applications.id"), nullable=False)
    lender_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("lenders.id"), nullable=False)
    product_id: Mapped[str | None] = mapped_column(UUID_TYPE, ForeignKey("lending_products.id"))
    rate: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False)
    points: Mapped[float | None] = mapped_column(Numeric(4, 2))
    apr: Mapped[float | None] = mapped_column(Numeric(5, 3))
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_payment: Mapped[float | None] = mapped_column(Numeric(10, 2))
    estimated_closing_costs: Mapped[float | None] = mapped_column(Numeric(10, 2))
    conditions: Mapped[dict | None] = mapped_column(JSON_TYPE)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    application: Mapped[LoanApplication] = relationship(back_populates="quotes")
