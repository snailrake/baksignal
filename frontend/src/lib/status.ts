import type { Availability, FuelType, QueueLevel, Station, StationStatus } from "../types/domain";

export const fuelOptions: Array<{ value: FuelType; label: string }> = [
  { value: "92", label: "АИ-92" },
  { value: "95", label: "АИ-95" },
  { value: "dt", label: "ДТ" },
];

export const availabilityOptions: Array<{ value: Availability; label: string }> = [
  { value: "yes", label: "Есть" },
  { value: "no", label: "Нет" },
  { value: "unknown", label: "Не уверен" },
];

export const queueOptions: Array<{ value: QueueLevel; label: string }> = [
  { value: "none", label: "Нет" },
  { value: "small", label: "Малая" },
  { value: "medium", label: "Средняя" },
  { value: "large", label: "Большая" },
  { value: "unknown", label: "Не знаю" },
];

export function getFuelStatus(station: Station, fuelType: FuelType): StationStatus | null {
  return station.statuses.find((status) => status.fuel_type === fuelType) ?? null;
}

export function isExpired(status: StationStatus | null): boolean {
  if (!status) {
    return true;
  }
  return new Date(status.expires_at).getTime() <= Date.now();
}

export function statusTone(status: StationStatus | null): "positive" | "negative" | "unknown" | "expired" {
  if (!status || isExpired(status)) {
    return "expired";
  }
  if (status.availability === "yes") {
    return "positive";
  }
  if (status.availability === "no") {
    return "negative";
  }
  return "unknown";
}

export function statusLabel(status: StationStatus | null): string {
  if (!status || isExpired(status)) {
    return "Нет свежих данных";
  }
  if (status.availability === "yes") {
    return "Есть";
  }
  if (status.availability === "no") {
    return "Нет";
  }
  return "Не уверен";
}

export function queueLabel(queueLevel: QueueLevel): string {
  return queueOptions.find((option) => option.value === queueLevel)?.label ?? "Не знаю";
}

export function formatUpdatedAt(status: StationStatus | null): string {
  if (!status) {
    return "не обновлялось";
  }

  const date = new Date(status.observed_at);
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

export function routeUrl(station: Station): string {
  return `https://yandex.ru/maps/?rtext=~${station.lat},${station.lon}&rtt=auto`;
}

