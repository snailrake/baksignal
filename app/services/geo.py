from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000


def distance_meters(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> float:
    lat_delta = radians(float(lat2 - lat1))
    lon_delta = radians(float(lon2 - lon1))
    first_lat = radians(float(lat1))
    second_lat = radians(float(lat2))

    haversine = sin(lat_delta / 2) ** 2 + cos(first_lat) * cos(second_lat) * sin(lon_delta / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(haversine))
