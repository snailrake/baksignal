from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.fuel_observation import FuelObservation
from app.models.status import StationFuelStatus


def default_confidence(source_type: str) -> int:
    return {
        "user": 60,
        "admin": 90,
        "public_news": 45,
        "imported": 35,
    }.get(source_type, 50)


def default_expires_at(source_type: str) -> datetime:
    minutes = settings.status_stale_minutes if source_type in {"user", "admin"} else 60
    return datetime.now(UTC) + timedelta(minutes=minutes)


async def upsert_current_status(session: AsyncSession, observation: FuelObservation) -> StationFuelStatus:
    existing = await session.scalar(
        select(StationFuelStatus).where(
            StationFuelStatus.station_id == observation.station_id,
            StationFuelStatus.fuel_type == observation.fuel_type,
        )
    )

    observed_at = observation.created_at or datetime.now(UTC)
    if existing is None:
        existing = StationFuelStatus(
            station_id=observation.station_id,
            fuel_type=observation.fuel_type,
            availability=observation.availability,
            queue_level=observation.queue_level,
            source_type=observation.source_type,
            confidence=observation.confidence,
            observation_id=observation.id,
            observed_at=observed_at,
            expires_at=observation.expires_at,
        )
        session.add(existing)
    else:
        existing.availability = observation.availability
        existing.queue_level = observation.queue_level
        existing.source_type = observation.source_type
        existing.confidence = observation.confidence
        existing.observation_id = observation.id
        existing.observed_at = observed_at
        existing.expires_at = observation.expires_at

    await session.flush()
    return existing

