from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.models.enums import StationVerificationStatus

UNKNOWN_ADDRESS = "Адрес не указан"

BRAND_ALIASES = {
    "bioil": "BiOil",
    "bi oil": "BiOil",
    "drive oil": "Drive Oil",
    "gp vimpel": "GP Vympel",
    "gp vympel": "GP Vympel",
    "gp vympel ": "GP Vympel",
    "vimpel": "GP Vympel",
    "vympel": "GP Vympel",
    "башнефть": "Башнефть",
    "газпром": "Газпром",
    "газпромнефть": "Газпромнефть",
    "лукойл": "Лукойл",
    "lukoil": "Лукойл",
    "lukoil-yugnefteprodukt": "Лукойл",
    "роснефть": "Роснефть",
    "тнк": "ТНК",
    "teboil": "Teboil",
    "тореко": "Торэко",
    "торэко": "Торэко",
    "toreko": "Торэко",
}

LIFECYCLE_KEYS = (
    "abandoned:amenity",
    "construction:amenity",
    "demolished:amenity",
    "destroyed:amenity",
    "disused:amenity",
    "historic:amenity",
    "planned:amenity",
    "proposed:amenity",
    "removed:amenity",
)

CLOSED_VALUES = {"abandoned", "closed", "construction", "demolished", "destroyed", "disused", "no", "removed"}


@dataclass(frozen=True)
class StationCandidate:
    source: str
    external_id: str
    name: str
    brand: str | None
    address: str
    district: str | None
    lat: Decimal
    lon: Decimal
    confidence: int
    is_active_signal: bool
    verification_status: StationVerificationStatus
    source_updated_at: datetime | None
    raw_payload: dict


def compact_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_match_text(value: str | None) -> str:
    normalized = compact_text(value).casefold()
    normalized = normalized.replace("ё", "е")
    normalized = re.sub(r"[\"'`«»№#.,;:()]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_brand(name: str | None, brand: str | None, operator: str | None = None) -> str | None:
    for value in (brand, name, operator):
        key = normalize_match_text(value)
        if not key:
            continue
        if key in BRAND_ALIASES:
            return BRAND_ALIASES[key]
        for alias, canonical in BRAND_ALIASES.items():
            if alias in key:
                return canonical
    return compact_text(brand) or None


def build_address(tags: dict[str, str]) -> str:
    street = compact_text(tags.get("addr:street"))
    house = compact_text(tags.get("addr:housenumber"))
    city = compact_text(tags.get("addr:city"))
    full = compact_text(tags.get("addr:full"))

    if full:
        return full
    if street and house:
        return f"{street}, {house}"
    if street:
        return street
    if city and house:
        return f"{city}, {house}"
    return UNKNOWN_ADDRESS


def has_closed_signal(tags: dict[str, str]) -> bool:
    if tags.get("amenity") != "fuel":
        return True
    if any(tags.get(key) == "fuel" for key in LIFECYCLE_KEYS):
        return True
    return any(normalize_match_text(tags.get(key)) in CLOSED_VALUES for key in ("disused", "abandoned", "closed"))


def quality_score(tags: dict[str, str], brand: str | None, address: str, is_active_signal: bool) -> int:
    if not is_active_signal:
        return 0

    score = 50
    if brand:
        score += 15
    if address != UNKNOWN_ADDRESS:
        score += 15
    if tags.get("opening_hours"):
        score += 5
    if any(tags.get(key) for key in ("fuel:diesel", "fuel:octane_92", "fuel:octane_95")):
        score += 10
    if tags.get("operator"):
        score += 5
    if tags.get("name"):
        score += 5

    return min(score, 100)


def verification_status_for(score: int, is_active_signal: bool) -> StationVerificationStatus:
    if not is_active_signal:
        return StationVerificationStatus.closed
    if score < 65:
        return StationVerificationStatus.needs_review
    return StationVerificationStatus.active
