import { useCallback, useState } from "react";

import type { Coordinates } from "../lib/geo";
import {
  getTelegramLocationManager,
  impactTelegram,
  notifyTelegram,
  openTelegramLocationSettings,
} from "../lib/telegram";

type LocationStatus = "idle" | "requesting" | "ready" | "denied" | "error";

type UserLocationState = {
  location: Coordinates | null;
  status: LocationStatus;
  error: string | null;
};

type BrowserPositionOptions = {
  enableHighAccuracy: boolean;
  maximumAge: number;
  timeout: number;
};

const browserPositionOptions: BrowserPositionOptions = {
  enableHighAccuracy: true,
  maximumAge: 60_000,
  timeout: 12_000,
};

class LocationPermissionDeniedError extends Error {
  constructor() {
    super("Геолокация запрещена. Открой настройки доступа, чтобы показать ближайшие АЗС.");
  }
}

function requestBrowserLocation(): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Геолокация недоступна в этом браузере"));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        });
      },
      (error) => reject(error),
      browserPositionOptions,
    );
  });
}

function requestTelegramLocation(): Promise<Coordinates | null> {
  const locationManager = getTelegramLocationManager();
  if (!locationManager || typeof locationManager.getLocation !== "function" || typeof locationManager.init !== "function") {
    return Promise.resolve(null);
  }

  return new Promise((resolve, reject) => {
    const getLocation = () => {
      if (locationManager.isAccessRequested && !locationManager.isAccessGranted) {
        reject(new LocationPermissionDeniedError());
        return;
      }

      if (!locationManager.isLocationAvailable) {
        resolve(null);
        return;
      }

      locationManager.getLocation((location) => {
        if (!location) {
          if (locationManager.isAccessRequested && !locationManager.isAccessGranted) {
            reject(new LocationPermissionDeniedError());
            return;
          }

          resolve(null);
          return;
        }

        resolve({
          lat: location.latitude,
          lon: location.longitude,
        });
      });
    };

    if (locationManager.isInited) {
      getLocation();
      return;
    }

    locationManager.init(getLocation);
  });
}

function locationErrorMessage(error: unknown): string {
  if (isPermissionDenied(error) || error instanceof LocationPermissionDeniedError) {
    return "Геолокация запрещена. Открой настройки доступа, чтобы показать ближайшие АЗС.";
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Не удалось получить геолокацию";
}

function isPermissionDenied(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    Number(error.code) === globalThis.GeolocationPositionError?.PERMISSION_DENIED
  );
}

function canOpenLocationSettings(): boolean {
  return typeof getTelegramLocationManager()?.openSettings === "function";
}

export function useUserLocation() {
  const [state, setState] = useState<UserLocationState>({
    location: null,
    status: "idle",
    error: null,
  });

  const requestLocation = useCallback(async () => {
    setState((current) => ({ ...current, status: "requesting", error: null }));
    impactTelegram("light");

    try {
      const telegramLocation = await requestTelegramLocation();
      const location = telegramLocation ?? (await requestBrowserLocation());

      setState({ location, status: "ready", error: null });
      notifyTelegram("success");
      return location;
    } catch (error) {
      const message = locationErrorMessage(error);
      const status = isPermissionDenied(error) || error instanceof LocationPermissionDeniedError ? "denied" : "error";

      setState({ location: null, status, error: message });
      notifyTelegram("error");
      return null;
    }
  }, []);

  const clearLocation = useCallback(() => {
    setState({ location: null, status: "idle", error: null });
  }, []);

  const openSettings = useCallback(() => {
    openTelegramLocationSettings();
  }, []);

  return {
    ...state,
    canOpenSettings: canOpenLocationSettings(),
    isRequesting: state.status === "requesting",
    requestLocation,
    clearLocation,
    openSettings,
  };
}
