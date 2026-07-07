from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Availability, FuelType, QueueLevel, SourceType


class FuelObservation(Base):
    __tablename__ = "fuel_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    fuel_type: Mapped[FuelType] = mapped_column(Enum(FuelType), index=True)
    availability: Mapped[Availability] = mapped_column(Enum(Availability), index=True)
    queue_level: Mapped[QueueLevel] = mapped_column(Enum(QueueLevel), default=QueueLevel.unknown)
    limit_liters: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), default=SourceType.user, index=True)
    source_url: Mapped[str | None] = mapped_column(String(500))
    telegram_user_id: Mapped[int | None] = mapped_column(index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    station = relationship("Station", back_populates="observations")

