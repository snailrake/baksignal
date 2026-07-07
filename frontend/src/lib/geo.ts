import type { Station } from "../types/domain";

export type Coordinates = {
  lat: number;
  lon: number;
};

const EARTH_RADIUS_M = 6_371_000;

function toRadians(value: number): number {
  return (value * Math.PI) / 180;
}

export function stationCoordinates(station: Station): Coordinates {
  return {
    lat: Number(station.lat),
    lon: Number(station.lon),
  };
}

export function distanceMeters(from: Coordinates, to: Coordinates): number {
  const latDelta = toRadians(to.lat - from.lat);
  const lonDelta = toRadians(to.lon - from.lon);
  const fromLat = toRadians(from.lat);
  const toLat = toRadians(to.lat);

  const haversine =
    Math.sin(latDelta / 2) ** 2 + Math.cos(fromLat) * Math.cos(toLat) * Math.sin(lonDelta / 2) ** 2;

  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(haversine));
}

export function distanceToStation(userLocation: Coordinates, station: Station): number {
  return distanceMeters(userLocation, stationCoordinates(station));
}

export function formatDistance(meters: number): string {
  if (meters < 950) {
    return `${Math.round(meters / 50) * 50} м`;
  }

  const kilometers = meters / 1000;
  return `${kilometers < 10 ? kilometers.toFixed(1) : Math.round(kilometers)} км`;
}
