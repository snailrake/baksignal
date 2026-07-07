from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StationVerificationStatus


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_station_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    brand: Mapped[str | None] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(240))
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    lon: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    source: Mapped[str] = mapped_column(String(40), default="manual")
    external_id: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[StationVerificationStatus] = mapped_column(
        Enum(StationVerificationStatus), default=StationVerificationStatus.active, index=True
    )
    quality_score: Mapped[int] = mapped_column(Integer, default=50)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    observations = relationship("FuelObservation", back_populates="station", cascade="all, delete-orphan")
    statuses = relationship("StationFuelStatus", back_populates="station", cascade="all, delete-orphan")
    sources = relationship("StationSource", back_populates="station", cascade="all, delete-orphan")
