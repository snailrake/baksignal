from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import Availability, FuelType, QueueLevel, SourceType, StationVerificationStatus
from app.schemas.datetime import serialize_utc_datetime


class StationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=80)
    address: str = Field(min_length=1, max_length=240)
    district: str | None = Field(default=None, max_length=80)
    lat: Decimal = Field(ge=-90, le=90)
    lon: Decimal = Field(ge=-180, le=180)
    source: str = Field(default="manual", max_length=40)
    external_id: str | None = Field(default=None, max_length=120)
    verification_status: StationVerificationStatus = StationVerificationStatus.active
    quality_score: int = Field(default=80, ge=0, le=100)


class StationStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fuel_type: FuelType
    availability: Availability
    queue_level: QueueLevel
    source_type: SourceType
    confidence: int
    observation_id: int
    observed_at: datetime
    expires_at: datetime

    @field_serializer("observed_at", "expires_at")
    def serialize_datetime(self, value: datetime) -> str:
        return serialize_utc_datetime(value)


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None
    address: str
    district: str | None
    lat: Decimal
    lon: Decimal
    source: str
    external_id: str | None
    verification_status: StationVerificationStatus
    quality_score: int
    last_verified_at: datetime | None
    statuses: list[StationStatusRead] = []

    @field_serializer("last_verified_at")
    def serialize_optional_datetime(self, value: datetime | None) -> str | None:
        return serialize_utc_datetime(value) if value else None
