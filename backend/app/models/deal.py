import uuid
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID_TYPE, JSON_TYPE, ARRAY_TYPE


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    property_id: Mapped[str | None] = mapped_column(UUID_TYPE, ForeignKey("properties.id"))
    source: Mapped[str] = mapped_column(String(50), default="manual")
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    raw_input: Mapped[dict | None] = mapped_column(JSON_TYPE)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(ARRAY_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="deals")
    property: Mapped["Property | None"] = relationship(back_populates="deals")
    analyses: Mapped[list["DealAnalysis"]] = relationship(back_populates="deal", order_by="DealAnalysis.version.desc()")


class DealAnalysis(Base):
    __tablename__ = "deal_analyses"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    assumptions: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    results: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    score_breakdown: Mapped[dict | None] = mapped_column(JSON_TYPE)
    model_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    deal: Mapped[Deal] = relationship(back_populates="analyses")
    projections: Mapped[list["ProFormaProjection"]] = relationship(back_populates="analysis")
    comparables: Mapped[list["ComparableSale"]] = relationship(back_populates="analysis")


class ProFormaProjection(Base):
    __tablename__ = "pro_forma_projections"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("deal_analyses.id", ondelete="CASCADE"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_income: Mapped[float] = mapped_column(Numeric(12, 2))
    vacancy_loss: Mapped[float] = mapped_column(Numeric(12, 2))
    operating_expenses: Mapped[float] = mapped_column(Numeric(12, 2))
    noi: Mapped[float] = mapped_column(Numeric(12, 2))
    debt_service: Mapped[float] = mapped_column(Numeric(12, 2))
    cash_flow: Mapped[float] = mapped_column(Numeric(12, 2))
    property_value: Mapped[float] = mapped_column(Numeric(14, 2))
    equity: Mapped[float] = mapped_column(Numeric(14, 2))
    cumulative_return: Mapped[float] = mapped_column(Numeric(12, 2))

    analysis: Mapped[DealAnalysis] = relationship(back_populates="projections")


class ComparableSale(Base):
    __tablename__ = "comparable_sales"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("deal_analyses.id", ondelete="CASCADE"), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    sale_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    sale_date: Mapped[datetime | None] = mapped_column(Date)
    distance_miles: Mapped[float | None] = mapped_column(Numeric(6, 3))
    similarity_score: Mapped[float | None] = mapped_column(Numeric(5, 3))
    adjustments: Mapped[dict | None] = mapped_column(JSON_TYPE)
    adjusted_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Numeric(3, 1))
    sqft: Mapped[int | None] = mapped_column(Integer)

    analysis: Mapped[DealAnalysis] = relationship(back_populates="comparables")


class InvestmentCriteria(Base):
    __tablename__ = "investment_criteria"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rules: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
