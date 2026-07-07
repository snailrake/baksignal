from typing import Annotated

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_telegram_user
from app.core.config import settings
from app.db.session import get_session
from app.models.station import Station
from app.schemas.observation import ObservationCreate, ObservationRead
from app.services.observation_service import create_observation_with_status

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("", response_model=ObservationRead, status_code=status.HTTP_201_CREATED)
async def create_observation(
    payload: ObservationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    telegram_user=Depends(get_optional_telegram_user),
) -> ObservationRead:
    station = await session.get(Station, payload.station_id)
    if station is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")

    data = payload.model_dump()
    if telegram_user is not None:
        data["telegram_user_id"] = telegram_user.id

    bot = None
    if settings.telegram_bot_token:
        bot = Bot(settings.telegram_bot_token)
    try:
        observation = await create_observation_with_status(session, station=station, data=data, bot=bot)
    finally:
        if bot is not None:
            await bot.session.close()

    return observation
