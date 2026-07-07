import { Clock, Fuel, Navigation } from "lucide-react";

import { formatDistance } from "../lib/geo";
import { formatUpdatedAt, getFuelStatus, statusLabel, statusTone } from "../lib/status";
import type { FuelType, Station } from "../types/domain";

type StationListProps = {
  stations: Station[];
  selectedStationId: number | null;
  fuelType: FuelType;
  distanceByStationId?: Map<number, number>;
  onSelect: (station: Station) => void;
};

export function StationList({ stations, selectedStationId, fuelType, distanceByStationId, onSelect }: StationListProps) {
  return (
    <div className="station-list" aria-label="АЗС">
      {stations.map((station) => {
        const status = getFuelStatus(station, fuelType);
        const tone = statusTone(status);
        const distance = distanceByStationId?.get(station.id);
        return (
          <button
            key={station.id}
            type="button"
            className={station.id === selectedStationId ? "station-row active" : "station-row"}
            onClick={() => onSelect(station)}
          >
            <span className={`status-dot status-dot--${tone}`} />
            <span className="station-row__main">
              <span className="station-row__title">
                {station.brand || station.name}
                {station.verification_status === "needs_review" && (
                  <span className="quality-badge">проверяем</span>
                )}
              </span>
              <span className="station-row__address">{station.address}</span>
            </span>
            <span className="station-row__meta">
              <span>
                <Fuel size={14} aria-hidden="true" />
                {statusLabel(status)}
              </span>
              <span>
                <Clock size={14} aria-hidden="true" />
                {formatUpdatedAt(status)}
              </span>
              {distance !== undefined && (
                <span>
                  <Navigation size={14} aria-hidden="true" />
                  {formatDistance(distance)}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
