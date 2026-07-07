from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fuel_observation import FuelObservation
from app.models.station import Station
from app.services.notification_service import notify_subscribers
from app.services.status_service import default_confidence, default_expires_at, upsert_current_status


async def create_observation_with_status(
    session: AsyncSession,
    *,
    station: Station,
    data: dict,
    bot: Bot | None = None,
    notify: bool = True,
) -> FuelObservation:
    source_type = data["source_type"]
    source_value = source_type.value if hasattr(source_type, "value") else str(source_type)

    if data.get("telegram_user_id") is None and source_value == "user":
        data["confidence"] = min(data.get("confidence") or 30, 30)
    else:
        data["confidence"] = data.get("confidence") or default_confidence(source_value)

    data["expires_at"] = default_expires_at(source_value)
    observation = FuelObservation(**data)
    session.add(observation)
    await session.flush()
    await session.refresh(observation)
    await upsert_current_status(session, observation)
    await session.commit()
    await session.refresh(observation)

    if notify and bot is not None:
        await notify_subscribers(session, bot, station, observation)

    return observation

