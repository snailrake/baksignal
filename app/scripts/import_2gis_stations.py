import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import StationVerificationStatus
from app.models.station import Station
from app.models.station_source import StationSource
from app.services.station_dedup import best_existing_match
from app.services.station_quality import StationCandidate, compact_text, normalize_brand, normalize_match_text

SOURCE = "2gis"
BASE_URL = "https://catalog.api.2gis.com"
TARGET_CITIES = ("Саратов", "Энгельс")
TARGET_CITY_POINTS = {
    "Саратов": "46.0343,51.5336",
    "Энгельс": "46.1267,51.4855",
}
TARGET_CITY_RADIUS_M = {
    "Саратов": 30_000,
    "Энгельс": 20_000,
}
RUBRIC_QUERIES = ("АЗС", "автозаправочные станции", "заправки")
EXCLUDED_RUBRIC_WORDS = ("агзс", "газозаправ", "метан", "пропан", "электрозаряд")
PAGE_SIZE = 10
MAX_PAGES = 5


@dataclass(frozen=True)
class TwoGisRegion:
    id: int
    name: str


def require_key() -> str:
    if not settings.dgis_api_key:
        raise RuntimeError("DGIS_API_KEY is required. Create a 2GIS API key and add it to .env.")
    return settings.dgis_api_key


def item_text(value: Any) -> str:
    if isinstance(value, str):
        return compact_text(value)
    if isinstance(value, dict):
        for key in ("name", "full_name", "short_name"):
            text = compact_text(value.get(key))
            if text:
                return text
    return ""


def item_brand(item: dict[str, Any]) -> str | None:
    brand = item.get("brand")
    org = item.get("org")
    return normalize_brand(item.get("name"), item_text(brand), item_text(org))


def item_address(item: dict[str, Any]) -> str:
    for key in ("full_address_name", "address_name"):
        value = compact_text(item.get(key))
        if value:
            return value

    address = item.get("address")
    if isinstance(address, dict):
        for key in ("name", "comment"):
            value = compact_text(address.get(key))
            if value:
                return value
    elif isinstance(address, str):
        value = compact_text(address)
        if value:
            return value

    return "Адрес не указан"


def point(item: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    raw = item.get("point")
    if not isinstance(raw, dict):
        return None

    lon = raw.get("lon")
    lat = raw.get("lat")
    if lat is None or lon is None:
        return None

    return Decimal(str(lat)), Decimal(str(lon))


def rubric_names(item: dict[str, Any]) -> list[str]:
    rubrics = item.get("rubrics")
    if not isinstance(rubrics, list):
        return []
    return [item_text(rubric) for rubric in rubrics if item_text(rubric)]


def adm_div_names(item: dict[str, Any]) -> list[str]:
    adm_div = item.get("adm_div")
    if not isinstance(adm_div, list):
        return []
    return [item_text(part) for part in adm_div if item_text(part)]


def infer_city(item: dict[str, Any], fallback_city: str) -> str | None:
    text = normalize_match_text(" ".join([item_address(item), item.get("name", ""), *adm_div_names(item)]))
    if "энгельс" in text:
        return "Энгельс"
    if "саратов" in text:
        return "Саратов"
    return fallback_city if fallback_city in TARGET_CITIES else None


def looks_like_gas_only(item: dict[str, Any]) -> bool:
    text = normalize_match_text(" ".join([item.get("name", ""), *rubric_names(item)]))
    return any(word in text for word in EXCLUDED_RUBRIC_WORDS)


def item_to_candidate(item: dict[str, Any], city: str) -> StationCandidate | None:
    coords = point(item)
    if coords is None or looks_like_gas_only(item):
        return None

    lat, lon = coords
    name = compact_text(item.get("name")) or "АЗС"
    brand = item_brand(item)
    inferred_city = infer_city(item, city)
    if inferred_city not in TARGET_CITIES:
        return None

    return StationCandidate(
        source=SOURCE,
        external_id=str(item["id"]),
        name=brand or name,
        brand=brand,
        address=item_address(item),
        district=inferred_city,
        lat=lat,
        lon=lon,
        confidence=100,
        is_active_signal=True,
        verification_status=StationVerificationStatus.active,
        source_updated_at=None,
        raw_payload=item,
    )


class TwoGisClient:
    def __init__(self, key: str) -> None:
        self.key = key
        self.client = httpx.AsyncClient(timeout=40)

    async def close(self) -> None:
        await self.client.aclose()

    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        response = await self.client.get(
            f"{BASE_URL}{path}",
            params={**params, "key": self.key},
            headers={"User-Agent": "Baksignal/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("meta", {}).get("code") not in (None, 200):
            raise RuntimeError(f"2GIS API error: {payload.get('meta')}")
        return payload

    async def get_optional(self, path: str, **params: Any) -> dict[str, Any]:
        response = await self.client.get(
            f"{BASE_URL}{path}",
            params={**params, "key": self.key},
            headers={"User-Agent": "Baksignal/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
        meta = payload.get("meta", {})
        if meta.get("code") == 404:
            return {"meta": meta, "result": {"items": []}}
        if meta.get("code") not in (None, 200):
            raise RuntimeError(f"2GIS API error: {meta}")
        return payload

    async def find_region(self, city: str) -> TwoGisRegion:
        payload = await self.get("/2.0/region/search", q=TARGET_CITY_POINTS.get(city, city))
        items = payload.get("result", {}).get("items", [])
        if not items:
            raise RuntimeError(f"2GIS region not found: {city}")

        exact = next(
            (
                item
                for item in items
                if normalize_match_text(item.get("name")) == normalize_match_text(city)
                or normalize_match_text(item.get("full_name")) == normalize_match_text(city)
            ),
            items[0],
        )
        return TwoGisRegion(id=int(exact["id"]), name=city)

    async def find_fuel_rubrics(self, region: TwoGisRegion) -> set[int]:
        rubric_ids: set[int] = set()
        for query in RUBRIC_QUERIES:
            payload = await self.get_optional("/2.0/catalog/rubric/search", region_id=region.id, q=query)
            for item in payload.get("result", {}).get("items", []):
                name = normalize_match_text(item.get("name") or item.get("full_name"))
                if not name or any(word in name for word in EXCLUDED_RUBRIC_WORDS):
                    continue
                if "азс" in name or "автозаправ" in name or "заправ" in name:
                    rubric_ids.add(int(item["id"]))
        return rubric_ids

    async def fetch_items(self, region: TwoGisRegion, city: str, rubric_ids: set[int]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        fields = ",".join(
            [
                "items.point",
                "items.address",
                "items.full_address_name",
                "items.rubrics",
                "items.brand",
                "items.org",
                "items.schedule",
                "items.adm_div",
            ]
        )

        while True:
            params: dict[str, Any] = {
                "region_id": region.id,
                "point": TARGET_CITY_POINTS[city],
                "radius": TARGET_CITY_RADIUS_M[city],
                "fields": fields,
                "page": page,
                "page_size": PAGE_SIZE,
            }
            if rubric_ids:
                params["rubric_id"] = ",".join(str(rubric_id) for rubric_id in sorted(rubric_ids))
            else:
                params["q"] = "АЗС"

            payload = await self.get_optional("/3.0/items", **params)
            page_items = payload.get("result", {}).get("items", [])
            items.extend(page_items)
            if len(page_items) < PAGE_SIZE or page >= MAX_PAGES:
                return items
            page += 1


def apply_candidate_to_station(station: Station, candidate: StationCandidate) -> None:
    station.name = candidate.name
    station.brand = candidate.brand
    station.address = candidate.address
    station.district = candidate.district
    station.lat = candidate.lat
    station.lon = candidate.lon
    station.source = candidate.source
    station.external_id = candidate.external_id
    station.verification_status = StationVerificationStatus.active
    station.quality_score = 100
    station.last_verified_at = datetime.now(UTC)
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
                is_active_signal=True,
                confidence=100,
                source_updated_at=None,
                raw_payload=candidate.raw_payload,
            )
        )
        return

    source.name = candidate.name
    source.brand = candidate.brand
    source.address = candidate.address
    source.lat = candidate.lat
    source.lon = candidate.lon
    source.is_active_signal = True
    source.confidence = 100
    source.fetched_at = datetime.now(UTC)
    source.raw_payload = candidate.raw_payload


async def fetch_candidates() -> list[StationCandidate]:
    client = TwoGisClient(require_key())
    try:
        candidates: list[StationCandidate] = []
        for city in TARGET_CITIES:
            region = await client.find_region(city)
            rubrics = await client.find_fuel_rubrics(region)
            items = await client.fetch_items(region, city, rubrics)
            candidates.extend(
                candidate
                for item in items
                if (candidate := item_to_candidate(item, city)) is not None
            )
        unique_candidates = {candidate.external_id: candidate for candidate in candidates}
        return list(unique_candidates.values())
    finally:
        await client.close()


async def import_candidates(candidates: list[StationCandidate], replace_directory: bool) -> dict[str, int]:
    stats = {"fetched": len(candidates), "created": 0, "updated": 0, "hidden": 0}
    seen_external_ids = {candidate.external_id for candidate in candidates}

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
            station = source_station_by_external_id.get(candidate.external_id) or best_existing_match(stations, candidate)
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
                    verification_status=StationVerificationStatus.active,
                    quality_score=100,
                    last_verified_at=datetime.now(UTC),
                )
                session.add(station)
                stations.append(station)
                stats["created"] += 1
            else:
                apply_candidate_to_station(station, candidate)
                stats["updated"] += 1

            upsert_source(station, candidate)

        if replace_directory:
            for station in stations:
                if station.source == SOURCE and station.external_id not in seen_external_ids:
                    station.verification_status = StationVerificationStatus.hidden
                    stats["hidden"] += 1

        await session.commit()

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Saratov/Engels fuel stations from 2GIS Places API.")
    parser.add_argument("--commit", action="store_true", help="Write results to the database.")
    parser.add_argument(
        "--replace-directory",
        action="store_true",
        help="Hide old 2GIS-linked stations missing from the latest 2GIS response.",
    )
    parser.add_argument(
        "--i-have-2gis-storage-permission",
        action="store_true",
        help="Required with --commit because default 2GIS API rules restrict saving/caching API products.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    candidates = await fetch_candidates()

    print(f"2GIS candidates fetched: {len(candidates)}")
    for candidate in sorted(candidates, key=lambda item: (item.district or "", item.brand or item.name, item.address))[:20]:
        print(f"- {candidate.district}: {candidate.brand or candidate.name} — {candidate.address}")

    if not args.commit:
        print("Dry run only. Re-run with --commit to write to the database.")
        return

    if not args.i_have_2gis_storage_permission:
        raise RuntimeError(
            "Refusing to save 2GIS data without explicit storage permission confirmation. "
            "Add --i-have-2gis-storage-permission only if your 2GIS terms allow this use."
        )

    stats = await import_candidates(candidates, args.replace_directory)
    print(
        "2GIS import complete: "
        f"fetched={stats['fetched']} created={stats['created']} updated={stats['updated']} hidden={stats['hidden']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
