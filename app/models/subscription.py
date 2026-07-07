from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import FuelType, QueueLevel


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", "fuel_type", "district", name="uq_subscription_user_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(index=True)
    fuel_type: Mapped[FuelType] = mapped_column(Enum(FuelType), index=True)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    center_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    center_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    radius_m: Mapped[int | None]
    notify_queue_max: Mapped[QueueLevel] = mapped_column(Enum(QueueLevel), default=QueueLevel.large)
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

