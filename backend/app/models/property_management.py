import uuid
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID_TYPE, JSON_TYPE, ARRAY_TYPE


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("properties.id"), nullable=False, index=True)
    unit_number: Mapped[str | None] = mapped_column(String(50))
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Numeric(3, 1))
    sqft: Mapped[int | None] = mapped_column(Integer)
    market_rent: Mapped[float | None] = mapped_column(Numeric(8, 2))
    status: Mapped[str] = mapped_column(String(50), default="vacant")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    property: Mapped["Property"] = relationship(back_populates="units")
    leases: Mapped[list["Lease"]] = relationship(back_populates="unit")
    maintenance_orders: Mapped[list["MaintenanceOrder"]] = relationship(back_populates="unit")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    screening_result: Mapped[dict | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    leases: Mapped[list["Lease"]] = relationship(back_populates="tenant")


class Lease(Base):
    __tablename__ = "leases"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("units.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("tenants.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    monthly_rent: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    security_deposit: Mapped[float | None] = mapped_column(Numeric(8, 2))
    pet_deposit: Mapped[float | None] = mapped_column(Numeric(8, 2))
    status: Mapped[str] = mapped_column(String(50), default="active")
    terms: Mapped[dict | None] = mapped_column(JSON_TYPE)
    lease_document_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    unit: Mapped[Unit] = relationship(back_populates="leases")
    tenant: Mapped[Tenant] = relationship(back_populates="leases")


class MaintenanceOrder(Base):
    __tablename__ = "maintenance_orders"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_id: Mapped[str] = mapped_column(UUID_TYPE, ForeignKey("units.id"), nullable=False)
    reported_by: Mapped[str | None] = mapped_column(UUID_TYPE)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="reported")
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    actual_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photos: Mapped[list | None] = mapped_column(ARRAY_TYPE)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    unit: Mapped[Unit] = relationship(back_populates="maintenance_orders")
