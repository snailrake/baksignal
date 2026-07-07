import { MapPinned, RefreshCcw, X } from "lucide-react";

import { formatUpdatedAt, getFuelStatus, queueLabel, routeUrl, statusLabel, statusTone } from "../lib/status";
import { openExternalUrl } from "../lib/telegram";
import type { FuelType, Station } from "../types/domain";

type StationSheetProps = {
  station: Station;
  fuelType: FuelType;
  onClose: () => void;
  onReport: () => void;
};

export function StationSheet({ station, fuelType, onClose, onReport }: StationSheetProps) {
  const status = getFuelStatus(station, fuelType);
  const tone = statusTone(status);

  return (
    <section className="station-sheet" aria-label="Выбранная АЗС">
      <div className="station-sheet__header">
        <div>
          <h2>{station.brand || station.name}</h2>
          <p>{station.address}</p>
          {station.verification_status === "needs_review" && (
            <span className="quality-note">Точка из карты, требуется подтверждение на месте</span>
          )}
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть">
          <X size={20} />
        </button>
      </div>

      <div className="status-summary">
        <div className={`status-pill status-pill--${tone}`}>{statusLabel(status)}</div>
        <div>
          <span>Обновлено</span>
          <strong>{formatUpdatedAt(status)}</strong>
        </div>
        <div>
          <span>Очередь</span>
          <strong>{status ? queueLabel(status.queue_level) : "нет данных"}</strong>
        </div>
      </div>

      <div className="station-sheet__actions">
        <button type="button" className="primary-button" onClick={onReport}>
          <RefreshCcw size={18} />
          Обновить статус
        </button>
        <button type="button" className="secondary-button" onClick={() => openExternalUrl(routeUrl(station))}>
          <MapPinned size={18} />
          Маршрут
        </button>
      </div>
    </section>
  );
}
