import { LocateFixed, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { createObservation, fetchStations } from "./api/client";
import { FuelFilter } from "./components/FuelFilter";
import { ReportDialog } from "./components/ReportDialog";
import { StationList } from "./components/StationList";
import { StationMap } from "./components/StationMap";
import { StationSheet } from "./components/StationSheet";
import { distanceToStation } from "./lib/geo";
import { notifyTelegram } from "./lib/telegram";
import { useUserLocation } from "./hooks/useUserLocation";
import type { FuelType, ObservationPayload, Station } from "./types/domain";

export function App() {
  const [fuelType, setFuelType] = useState<FuelType>("95");
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const userLocation = useUserLocation();

  const selectedStation = useMemo(
    () => stations.find((station) => station.id === selectedStationId) ?? null,
    [selectedStationId, stations],
  );

  const distanceByStationId = useMemo(() => {
    const location = userLocation.location;
    if (!location) {
      return new Map<number, number>();
    }

    return new Map(stations.map((station) => [station.id, distanceToStation(location, station)]));
  }, [stations, userLocation.location]);

  const filteredStations = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("ru-RU");
    const visibleStations = normalizedQuery
      ? stations.filter((station) => {
          const haystack = `${station.name} ${station.brand ?? ""} ${station.address} ${station.district ?? ""}`;
          return haystack.toLocaleLowerCase("ru-RU").includes(normalizedQuery);
        })
      : stations;

    if (!userLocation.location) {
      return visibleStations;
    }

    return [...visibleStations].sort((first, second) => {
      const firstDistance = distanceByStationId.get(first.id) ?? Number.MAX_SAFE_INTEGER;
      const secondDistance = distanceByStationId.get(second.id) ?? Number.MAX_SAFE_INTEGER;
      return firstDistance - secondDistance;
    });
  }, [distanceByStationId, query, stations, userLocation.location]);

  const loadStations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const nextStations = await fetchStations();
      setStations(nextStations);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось загрузить АЗС");
      notifyTelegram("error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStations();
  }, [loadStations]);

  async function submitObservation(payload: ObservationPayload): Promise<void> {
    setIsSubmitting(true);
    setError(null);
    try {
      await createObservation(payload);
      notifyTelegram("success");
      setIsReportOpen(false);
      await loadStations();
    } catch (requestError) {
      notifyTelegram("error");
      setError(requestError instanceof Error ? requestError.message : "Не удалось сохранить статус");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function toggleNearbyMode(): Promise<void> {
    if (userLocation.location) {
      userLocation.clearLocation();
      return;
    }

    await userLocation.requestLocation();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>БакСигнал</h1>
          <p>Саратов и Энгельс</p>
        </div>
        <button type="button" className="icon-button" onClick={() => void loadStations()} aria-label="Обновить">
          <RefreshCw size={20} />
        </button>
      </header>

      <section className="control-panel" aria-label="Фильтры">
        <FuelFilter value={fuelType} onChange={setFuelType} />
        <label className="search-field">
          <Search size={18} aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Найти АЗС, бренд или район"
          />
        </label>
        <button
          type="button"
          className={userLocation.location ? "location-button active" : "location-button"}
          onClick={() => void toggleNearbyMode()}
          disabled={userLocation.isRequesting}
        >
          <LocateFixed size={18} />
          {userLocation.isRequesting ? "Ищем" : "Рядом"}
        </button>
      </section>

      <section className="workspace">
        <StationMap
          stations={filteredStations}
          selectedStationId={selectedStationId}
          fuelType={fuelType}
          userLocation={userLocation.location}
          onSelect={(station) => setSelectedStationId(station.id)}
        />

        <aside className="side-panel">
          <div className="side-panel__header">
            <span>{isLoading ? "Загружаем" : `${filteredStations.length} АЗС${userLocation.location ? " рядом" : ""}`}</span>
          </div>
          {error && <div className="error-banner">{error}</div>}
          {userLocation.error && (
            <div className="error-banner error-banner--action">
              <span>{userLocation.error}</span>
              {userLocation.canOpenSettings && (
                <button type="button" onClick={userLocation.openSettings}>
                  Настройки
                </button>
              )}
            </div>
          )}
          <StationList
            stations={filteredStations}
            selectedStationId={selectedStationId}
            fuelType={fuelType}
            distanceByStationId={distanceByStationId}
            onSelect={(station) => setSelectedStationId(station.id)}
          />
        </aside>
      </section>

      {selectedStation && (
        <StationSheet
          station={selectedStation}
          fuelType={fuelType}
          onClose={() => setSelectedStationId(null)}
          onReport={() => setIsReportOpen(true)}
        />
      )}

      {selectedStation && isReportOpen && (
        <ReportDialog
          station={selectedStation}
          fuelType={fuelType}
          submitting={isSubmitting}
          onSubmit={submitObservation}
          onClose={() => setIsReportOpen(false)}
        />
      )}
    </main>
  );
}
