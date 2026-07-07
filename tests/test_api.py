from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models import FuelObservation, Station, StationFuelStatus, Subscription  # noqa: F401


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()


async def test_station_observation_updates_current_status(client: AsyncClient) -> None:
    station_response = await client.post(
        "/stations",
        json={
            "name": "АЗС Тест",
            "brand": "ТестОйл",
            "address": "Саратов, тестовая улица, 1",
            "district": "Ленинский",
            "lat": "51.600000",
            "lon": "45.970000",
            "source": "manual",
            "external_id": "test-1",
        },
    )
    assert station_response.status_code == 201
    station_id = station_response.json()["id"]

    observation_response = await client.post(
        "/observations",
        json={
            "station_id": station_id,
            "fuel_type": "95",
            "availability": "yes",
            "queue_level": "small",
            "limit_liters": 30,
            "source_type": "user",
            "telegram_user_id": 12345,
        },
    )
    assert observation_response.status_code == 201
    observation = observation_response.json()
    assert observation["confidence"] == 60

    station_with_status_response = await client.get(f"/stations/{station_id}")
    assert station_with_status_response.status_code == 200
    statuses = station_with_status_response.json()["statuses"]
    assert len(statuses) == 1
    assert statuses[0]["fuel_type"] == "95"
    assert statuses[0]["availability"] == "yes"
    assert statuses[0]["queue_level"] == "small"


async def test_subscription_requires_telegram_user(client: AsyncClient) -> None:
    response = await client.post(
        "/subscriptions",
        json={
            "fuel_type": "92",
            "district": "Заводской",
        },
    )
    assert response.status_code == 401

