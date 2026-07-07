from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Availability
from app.models.fuel_observation import FuelObservation
from app.models.station import Station
from app.models.subscription import Subscription


def distance_m(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> int:
    earth_radius_m = 6_371_000
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
        radians,
        [float(lat1), float(lon1), float(lat2), float(lon2)],
    )
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    return int(2 * earth_radius_m * asin(sqrt(a)))


def subscription_matches_station(subscription: Subscription, station: Station) -> bool:
    if subscription.district and station.district:
        return subscription.district.casefold() == station.district.casefold()

    if subscription.center_lat and subscription.center_lon and subscription.radius_m:
        return (
            distance_m(subscription.center_lat, subscription.center_lon, station.lat, station.lon)
            <= subscription.radius_m
        )

    return False


async def notify_subscribers(
    session: AsyncSession,
    bot: Bot,
    station: Station,
    observation: FuelObservation,
) -> int:
    if observation.availability != Availability.yes:
        return 0

    result = await session.scalars(
        select(Subscription).where(
            Subscription.active.is_(True),
            Subscription.fuel_type == observation.fuel_type,
        )
    )

    sent = 0
    for subscription in result:
        if subscription.telegram_user_id == observation.telegram_user_id:
            continue
        if not subscription_matches_station(subscription, station):
            continue

        limit = f"\nЛимит: {observation.limit_liters} л" if observation.limit_liters else ""
        await bot.send_message(
            subscription.telegram_user_id,
            (
                f"Появился сигнал по {observation.fuel_type.value}\n"
                f"{station.name}\n"
                f"{station.address}\n"
                f"Очередь: {observation.queue_level.value}{limit}"
            ),
        )
        sent += 1

    return sent

