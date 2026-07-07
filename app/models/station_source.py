from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StationSource(Base):
    __tablename__ = "station_sources"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_station_sources_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(160))
    brand: Mapped[str | None] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(240))
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    lon: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    is_active_signal: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    station = relationship("Station", back_populates="sources")
