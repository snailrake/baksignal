import { getTelegramInitData } from "../lib/telegram";
import type { ObservationPayload, Station } from "../types/domain";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const initData = getTelegramInitData();
  if (initData) {
    headers.set("X-Telegram-Init-Data", initData);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function fetchStations(): Promise<Station[]> {
  return request<Station[]>("/stations");
}

export async function createObservation(payload: ObservationPayload): Promise<void> {
  await request("/observations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
