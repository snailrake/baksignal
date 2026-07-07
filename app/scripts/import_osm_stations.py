import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.enums import StationVerificationStatus
from app.models.station import Station
from app.models.station_source import StationSource
from app.services.station_dedup import best_existing_match, is_duplicate_candidate
from app.services.station_quality import (
    StationCandidate,
    build_address,
    compact_text,
    has_closed_signal,
    normalize_brand,
    quality_score,
    verification_status_for,
)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SOURCE = "osm"


def build_query() -> str:
    return """
    [out:json][timeout:120];
    area["ISO3166-2"="RU-SAR"][admin_level=4]->.searchArea;
    (
      nwr["amenity"="fuel"](area.searchArea);
    );
    out center tags meta;
    """


def get_coordinates(element: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")
    if lat is None or lon is None:
        return None
    return Decimal(str(lat)), Decimal(str(lon))


def parse_osm_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def infer_district(tags: dict[str, str]) -> str | None:
    for key in ("addr:city", "addr:district", "addr:subdistrict"):
        value = compact_text(tags.get(key))
        if value:
            return value
    return None


def element_to_candidate(element: dict[str, Any]) -> StationCandidate | None:
    coords = get_coordinates(element)
    if coords is None:
        return None

    lat, lon = coords
    tags = element.get("tags", {})
    raw_name = compact_text(tags.get("name") or tags.get("brand") or tags.get("operator") or "АЗС")
    brand = normalize_brand(raw_name, tags.get("brand"), tags.get("operator"))
    address = build_address(tags)
    is_active_signal = not has_closed_signal(tags)
    confidence = quality_score(tags, brand, address, is_active_signal)

    return StationCandidate(
        source=SOURCE,
        external_id=f"{element['type']}/{element['id']}",
        name=raw_name,
        brand=brand,
        address=address,
        district=infer_district(tags),
        lat=lat,
        lon=lon,
        confidence=confidence,
        is_active_signal=is_active_signal,
        verification_status=verification_status_for(confidence, is_active_signal),
        source_updated_at=parse_osm_timestamp(element.get("timestamp")),
        raw_payload=element,
    )


async def fetch_osm_candidates() -> list[StationCandidate]:
    async with httpx.AsyncClient(timeout=150) as client:
        response = await client.post(
            OVERPASS_URL,
            content=build_query(),
            headers={"Content-Type": "text/plain", "User-Agent": "Baksignal/0.1"},
        )
        response.raise_for_status()
        payload = response.json()

    candidates = [element_to_candidate(element) for element in payload.get("elements", [])]
    return [candidate for candidate in candidates if candidate is not None]


def apply_candidate_to_station(station: Station, candidate: StationCandidate) -> None:
    if candidate.confidence >= station.quality_score or station.source == candidate.source:
        station.name = candidate.name
        station.brand = candidate.brand
        station.address = candidate.address
        station.district = candidate.district
        station.lat = candidate.lat
        station.lon = candidate.lon
        station.source = candidate.source
        station.external_id = candidate.external_id

    station.quality_score = max(station.quality_score, candidate.confidence)
    station.last_verified_at = datetime.now(UTC)
    if candidate.verification_status == StationVerificationStatus.closed:
        station.verification_status = StationVerificationStatus.closed
        station.closed_at = datetime.now(UTC)
    elif station.verification_status != StationVerificationStatus.hidden:
        station.verification_status = candidate.verification_status
        station.closed_at = None


def upsert_source(station: Station, candidate: StationCandidate) -> None:
    source = next(
        (
            station_source
            for station_source in station.sources
            if station_source.source == candidate.source and station_source.external_id == candidate.external_id
        ),
        None,
    )
    if source is None:
        station.sources.append(
            StationSource(
                source=candidate.source,
                external_id=candidate.external_id,
                name=candidate.name,
                brand=candidate.brand,
                address=candidate.address,
                lat=candidate.lat,
                lon=candidate.lon,
                is_active_signal=candidate.is_active_signal,
                confidence=candidate.confidence,
                source_updated_at=candidate.source_updated_at,
                raw_payload=candidate.raw_payload,
            )
        )
        return

    source.name = candidate.name
    source.brand = candidate.brand
    source.address = candidate.address
    source.lat = candidate.lat
    source.lon = candidate.lon
    source.is_active_signal = candidate.is_active_signal
    source.confidence = candidate.confidence
    source.source_updated_at = candidate.source_updated_at
    source.fetched_at = datetime.now(UTC)
    source.raw_payload = candidate.raw_payload


def hide_duplicate_stations(stations: list[Station]) -> int:
    hidden = 0
    active_candidates = [
        station
        for station in stations
        if station.verification_status in {StationVerificationStatus.active, StationVerificationStatus.needs_review}
    ]

    for index, station in enumerate(active_candidates):
        if station.verification_status == StationVerificationStatus.hidden:
            continue
        for other in active_candidates[index + 1 :]:
            if other.verification_status == StationVerificationStatus.hidden:
                continue
            candidate = StationCandidate(
                source=other.source,
                external_id=other.external_id or f"station/{other.id}",
                name=other.name,
                brand=other.brand,
                address=other.address,
                district=other.district,
                lat=other.lat,
                lon=other.lon,
                confidence=other.quality_score,
                is_active_signal=True,
                verification_status=other.verification_status,
                source_updated_at=other.last_verified_at,
                raw_payload={},
            )
            if not is_duplicate_candidate(station, candidate):
                continue

            keeper, duplicate = (
                (station, other)
                if (station.quality_score, station.id or 0) >= (other.quality_score, other.id or 0)
                else (other, station)
            )
            duplicate.verification_status = StationVerificationStatus.hidden
            duplicate.quality_score = min(duplicate.quality_score, keeper.quality_score)
            hidden += 1

    return hidden


async def import_stations() -> dict[str, int]:
    candidates = await fetch_osm_candidates()
    seen_external_ids = {candidate.external_id for candidate in candidates}

    stats = {"fetched": len(candidates), "created": 0, "updated": 0, "hidden_duplicates": 0, "stale_hidden": 0}

    async with SessionLocal() as session:
        stations = list((await session.scalars(select(Station).options(selectinload(Station.sources)))).unique())
        station_by_id = {station.id: station for station in stations}
        sources = list(await session.scalars(select(StationSource).where(StationSource.source == SOURCE)))
        source_station_by_external_id = {
            source.external_id: station_by_id[source.station_id]
            for source in sources
            if source.station_id in station_by_id
        }

        for candidate in candidates:
            station = source_station_by_external_id.get(candidate.external_id)
            if station is None:
                station = next(
                    (
                        existing
                        for existing in stations
                        if existing.source == SOURCE and existing.external_id == candidate.external_id
                    ),
                    None,
                )

            if station is None:
                station = best_existing_match(stations, candidate)

            if station is None:
                station = Station(
                    name=candidate.name,
                    brand=candidate.brand,
                    address=candidate.address,
                    district=candidate.district,
                    lat=candidate.lat,
                    lon=candidate.lon,
                    source=candidate.source,
                    external_id=candidate.external_id,
                    verification_status=candidate.verification_status,
                    quality_score=candidate.confidence,
                    last_verified_at=datetime.now(UTC),
                    closed_at=datetime.now(UTC)
                    if candidate.verification_status == StationVerificationStatus.closed
                    else None,
                )
                session.add(station)
                stations.append(station)
                stats["created"] += 1
            else:
                apply_candidate_to_station(station, candidate)
                stats["updated"] += 1

            upsert_source(station, candidate)

        for station in stations:
            if (
                station.source == SOURCE
                and station.external_id
                and station.external_id not in seen_external_ids
                and station.verification_status != StationVerificationStatus.hidden
            ):
                station.verification_status = StationVerificationStatus.hidden
                stats["stale_hidden"] += 1

        stats["hidden_duplicates"] = hide_duplicate_stations(stations)
        await session.commit()

    return stats


async def main() -> None:
    stats = await import_stations()
    print(
        "OSM import complete: "
        f"fetched={stats['fetched']} created={stats['created']} updated={stats['updated']} "
        f"hidden_duplicates={stats['hidden_duplicates']} stale_hidden={stats['stale_hidden']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
