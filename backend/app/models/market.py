import uuid
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import UUID_TYPE, JSON_TYPE


class MarketMetrics(Base):
    __tablename__ = "market_metrics"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    geo_type: Mapped[str] = mapped_column(String(20), nullable=False)
    month: Mapped[datetime] = mapped_column(Date, nullable=False)
    median_list_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    median_sold_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    median_price_per_sqft: Mapped[float | None] = mapped_column(Numeric(8, 2))
    median_dom: Mapped[int | None] = mapped_column(Integer)
    active_inventory: Mapped[int | None] = mapped_column(Integer)
    monthly_sales: Mapped[int | None] = mapped_column(Integer)
    absorption_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))
    median_rent: Mapped[float | None] = mapped_column(Numeric(8, 2))
    rent_yield: Mapped[float | None] = mapped_column(Numeric(5, 3))
    yoy_price_change: Mapped[float | None] = mapped_column(Numeric(5, 2))
    yoy_rent_change: Mapped[float | None] = mapped_column(Numeric(5, 2))
    population: Mapped[int | None] = mapped_column(Integer)
    population_growth: Mapped[float | None] = mapped_column(Numeric(5, 3))
    median_income: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unemployment_rate: Mapped[float | None] = mapped_column(Numeric(4, 2))
    crime_index: Mapped[float | None] = mapped_column(Numeric(5, 2))
    school_rating: Mapped[float | None] = mapped_column(Numeric(3, 1))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class MarketForecast(Base):
    __tablename__ = "market_forecasts"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    forecast_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    p10: Mapped[float | None] = mapped_column(Numeric(6, 3))
    p50: Mapped[float | None] = mapped_column(Numeric(6, 3))
    p90: Mapped[float | None] = mapped_column(Numeric(6, 3))
    model_version: Mapped[str | None] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class RentComp(Base):
    __tablename__ = "rent_comps"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id: Mapped[str | None] = mapped_column(UUID_TYPE)
    address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Numeric(3, 1))
    sqft: Mapped[int | None] = mapped_column(Integer)
    rent_amount: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    source: Mapped[str | None] = mapped_column(String(50))
    effective_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class NeighborhoodScore(Base):
    __tablename__ = "neighborhood_scores"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    geo_type: Mapped[str] = mapped_column(String(20), nullable=False)
    overall_grade: Mapped[str | None] = mapped_column(String(2))
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    scores: Mapped[dict | None] = mapped_column(JSON_TYPE)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
