from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.models.enums import FuelType, QueueLevel
from app.schemas.datetime import serialize_utc_datetime


class SubscriptionCreate(BaseModel):
    telegram_user_id: int | None = None
    fuel_type: FuelType
    district: str | None = Field(default=None, max_length=80)
    center_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    center_lon: Decimal | None = Field(default=None, ge=-180, le=180)
    radius_m: int | None = Field(default=None, ge=100, le=100_000)
    notify_queue_max: QueueLevel = QueueLevel.large

    @model_validator(mode="after")
    def district_or_radius_required(self):
        has_radius = self.center_lat is not None and self.center_lon is not None and self.radius_m is not None
        if not self.district and not has_radius:
            raise ValueError("Provide either district or center_lat, center_lon and radius_m")
        return self


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_user_id: int
    fuel_type: FuelType
    district: str | None
    center_lat: Decimal | None
    center_lon: Decimal | None
    radius_m: int | None
    notify_queue_max: QueueLevel
    active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return serialize_utc_datetime(value)
