from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_telegram_user
from app.db.session import get_session
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionRead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: SubscriptionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    telegram_user=Depends(get_optional_telegram_user),
) -> Subscription:
    data = payload.model_dump()
    if telegram_user is not None:
        data["telegram_user_id"] = telegram_user.id
    if data["telegram_user_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram user is required for subscriptions",
        )

    existing = await session.scalar(
        select(Subscription).where(
            Subscription.telegram_user_id == data["telegram_user_id"],
            Subscription.fuel_type == data["fuel_type"],
            Subscription.district == data["district"],
        )
    )
    if existing is not None:
        existing.active = True
        existing.center_lat = data["center_lat"]
        existing.center_lon = data["center_lon"]
        existing.radius_m = data["radius_m"]
        existing.notify_queue_max = data["notify_queue_max"]
        await session.commit()
        await session.refresh(existing)
        return existing

    subscription = Subscription(**data)
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


@router.get("/me", response_model=list[SubscriptionRead])
async def list_my_subscriptions(
    session: Annotated[AsyncSession, Depends(get_session)],
    telegram_user=Depends(get_optional_telegram_user),
) -> list[Subscription]:
    if telegram_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram user is required for subscriptions",
        )

    result = await session.scalars(
        select(Subscription)
        .where(Subscription.telegram_user_id == telegram_user.id)
        .order_by(Subscription.created_at.desc())
    )
    return list(result)
