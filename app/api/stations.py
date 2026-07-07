from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.enums import FuelType, StationVerificationStatus
from app.models.station import Station
from app.models.status import StationFuelStatus
from app.schemas.station import StationCreate, StationRead

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationRead])
async def list_stations(
    session: Annotated[AsyncSession, Depends(get_session)],
    fuel_type: Annotated[FuelType | None, Query()] = None,
    district: Annotated[str | None, Query(max_length=80)] = None,
    include_unverified: Annotated[bool, Query()] = False,
) -> list[Station]:
    stmt = select(Station).options(selectinload(Station.statuses)).order_by(Station.brand, Station.name)
    if not include_unverified:
        stmt = stmt.where(
            Station.verification_status.in_(
                [StationVerificationStatus.active, StationVerificationStatus.needs_review]
            )
        )
    if district:
        stmt = stmt.where(Station.district == district)
    if fuel_type:
        stmt = stmt.join(StationFuelStatus).where(StationFuelStatus.fuel_type == fuel_type)

    result = await session.scalars(stmt)
    return list(result.unique())


@router.post("", response_model=StationRead, status_code=status.HTTP_201_CREATED)
async def create_station(
    payload: StationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Station:
    station = Station(**payload.model_dump())
    session.add(station)
    await session.commit()
    created_station = await session.scalar(
        select(Station)
        .where(Station.id == station.id)
        .options(selectinload(Station.statuses))
    )
    if created_station is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Station was not saved")
    return created_station


@router.get("/{station_id}", response_model=StationRead)
async def get_station(
    station_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Station:
    station = await session.scalar(
        select(Station)
        .where(Station.id == station_id)
        .options(selectinload(Station.statuses))
    )
    if station is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")
    return station
