from __future__ import annotations

from app.models.station import Station
from app.services.geo import distance_meters
from app.services.station_quality import StationCandidate, normalize_match_text

STRICT_DISTANCE_M = 45
LOOSE_DISTANCE_M = 85


def same_brand(station: Station, candidate: StationCandidate) -> bool:
    if not station.brand or not candidate.brand:
        return False
    return normalize_match_text(station.brand) == normalize_match_text(candidate.brand)


def similar_name_or_address(station: Station, candidate: StationCandidate) -> bool:
    station_name = normalize_match_text(station.name)
    candidate_name = normalize_match_text(candidate.name)
    station_address = normalize_match_text(station.address)
    candidate_address = normalize_match_text(candidate.address)

    has_name_overlap = bool(station_name and candidate_name and (station_name in candidate_name or candidate_name in station_name))
    has_address_overlap = bool(
        station_address
        and candidate_address
        and station_address != normalize_match_text("Адрес не указан")
        and (station_address in candidate_address or candidate_address in station_address)
    )
    return has_name_overlap or has_address_overlap


def is_duplicate_candidate(station: Station, candidate: StationCandidate) -> bool:
    distance = distance_meters(station.lat, station.lon, candidate.lat, candidate.lon)
    if distance <= STRICT_DISTANCE_M and (same_brand(station, candidate) or similar_name_or_address(station, candidate)):
        return True
    if distance <= LOOSE_DISTANCE_M and same_brand(station, candidate) and similar_name_or_address(station, candidate):
        return True
    return False


def best_existing_match(stations: list[Station], candidate: StationCandidate) -> Station | None:
    matches = [station for station in stations if is_duplicate_candidate(station, candidate)]
    if not matches:
        return None
    return min(matches, key=lambda station: distance_meters(station.lat, station.lon, candidate.lat, candidate.lon))
