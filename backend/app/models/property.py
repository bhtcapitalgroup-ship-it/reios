import uuid
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID_TYPE, JSON_TYPE, ARRAY_TYPE


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    county_fips: Mapped[str | None] = mapped_column(String(5))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    property_type: Mapped[str] = mapped_column(String(50), default="sfr")
    year_built: Mapped[int | None] = mapped_column(Integer)
    sqft: Mapped[int | None] = mapped_column(Integer)
    lot_sqft: Mapped[int | None] = mapped_column(Integer)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Numeric(3, 1))
    stories: Mapped[int | None] = mapped_column(Integer)
    garage_spaces: Mapped[int] = mapped_column(Integer, default=0)
    pool: Mapped[bool] = mapped_column(default=False)
    features: Mapped[dict | None] = mapped_column(JSON_TYPE)
    data_sources: Mapped[dict | None] = mapped_column(JSON_TYPE)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    deals: Mapped[list["Deal"]] = relationship(back_populates="property")
    listings: Mapped[list["PropertyListing"]] = relationship(back_populates="property")
    tax_assessments: Mapped[list["TaxAssessment"]] = relationship(back_populates="property")
    units: Mapped[list["Unit"]] = relationship(back_populates="property")


class PropertyListing(Base):
    __tablename__ = "property_listings"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("properties.id"), nullable=False)
    mls_id: Mapped[str | None] = mapped_column(String(50))
    mls_source: Mapped[str | None] = mapped_column(String(100))
    list_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    list_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="active")
    sold_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    sold_date: Mapped[datetime | None] = mapped_column(Date)
    days_on_market: Mapped[int | None] = mapped_column(Integer)
    agent_info: Mapped[dict | None] = mapped_column(JSON_TYPE)
    photos: Mapped[list | None] = mapped_column(ARRAY_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    property: Mapped[Property] = relationship(back_populates="listings")


class TaxAssessment(Base):
    __tablename__ = "tax_assessments"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("properties.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    assessed_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    land_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    improvement_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    tax_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    exemptions: Mapped[dict | None] = mapped_column(JSON_TYPE)

    property: Mapped[Property] = relationship(back_populates="tax_assessments")
