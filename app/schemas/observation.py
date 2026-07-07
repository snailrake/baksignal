from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import Availability, FuelType, QueueLevel, SourceType
from app.schemas.datetime import serialize_utc_datetime


class ObservationCreate(BaseModel):
    station_id: int
    fuel_type: FuelType
    availability: Availability
    queue_level: QueueLevel = QueueLevel.unknown
    limit_liters: int | None = Field(default=None, ge=1, le=500)
    price: Decimal | None = Field(default=None, ge=1, le=500)
    source_type: SourceType = SourceType.user
    source_url: str | None = Field(default=None, max_length=500)
    telegram_user_id: int | None = None
    confidence: int | None = Field(default=None, ge=1, le=100)

    @field_validator("source_url")
    @classmethod
    def source_url_required_for_public_news(cls, value: str | None, info):
        source_type = info.data.get("source_type")
        if source_type == SourceType.public_news and not value:
            raise ValueError("source_url is required for public_news observations")
        return value


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    fuel_type: FuelType
    availability: Availability
    queue_level: QueueLevel
    limit_liters: int | None
    price: Decimal | None
    source_type: SourceType
    source_url: str | None
    telegram_user_id: int | None
    confidence: int
    expires_at: datetime
    created_at: datetime

    @field_serializer("expires_at", "created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return serialize_utc_datetime(value)
