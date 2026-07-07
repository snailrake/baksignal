from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Availability, FuelType, QueueLevel, SourceType


class StationFuelStatus(Base):
    __tablename__ = "station_fuel_statuses"
    __table_args__ = (UniqueConstraint("station_id", "fuel_type", name="uq_status_station_fuel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    fuel_type: Mapped[FuelType] = mapped_column(Enum(FuelType), index=True)
    availability: Mapped[Availability] = mapped_column(Enum(Availability), index=True)
    queue_level: Mapped[QueueLevel] = mapped_column(Enum(QueueLevel), default=QueueLevel.unknown)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    observation_id: Mapped[int] = mapped_column(ForeignKey("fuel_observations.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    station = relationship("Station", back_populates="statuses")

