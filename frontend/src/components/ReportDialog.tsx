import { useState } from "react";
import { Send, X } from "lucide-react";

import { availabilityOptions, queueOptions } from "../lib/status";
import type { Availability, FuelType, ObservationPayload, QueueLevel, Station } from "../types/domain";

type ReportDialogProps = {
  station: Station;
  fuelType: FuelType;
  submitting: boolean;
  onSubmit: (payload: ObservationPayload) => Promise<void>;
  onClose: () => void;
};

export function ReportDialog({ station, fuelType, submitting, onSubmit, onClose }: ReportDialogProps) {
  const [availability, setAvailability] = useState<Availability>("yes");
  const [queueLevel, setQueueLevel] = useState<QueueLevel>("small");
  const [limitLiters, setLimitLiters] = useState("");

  const parsedLimit = limitLiters.trim() ? Number(limitLiters) : null;
  const canSubmit = parsedLimit === null || (Number.isFinite(parsedLimit) && parsedLimit > 0);

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="report-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (!canSubmit || submitting) {
            return;
          }
          void onSubmit({
            station_id: station.id,
            fuel_type: fuelType,
            availability,
            queue_level: queueLevel,
            limit_liters: parsedLimit,
            source_type: "user",
          });
        }}
      >
        <div className="report-dialog__header">
          <div>
            <h2>Обновить статус</h2>
            <p>{station.brand || station.name}</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть">
            <X size={20} />
          </button>
        </div>

        <fieldset>
          <legend>Наличие</legend>
          <div className="segmented-grid">
            {availabilityOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={availability === option.value ? "choice active" : "choice"}
                onClick={() => setAvailability(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>Очередь</legend>
          <div className="segmented-grid">
            {queueOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={queueLevel === option.value ? "choice active" : "choice"}
                onClick={() => setQueueLevel(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="field-label">
          Лимит, литров
          <input
            inputMode="numeric"
            min="1"
            placeholder="если есть"
            value={limitLiters}
            onChange={(event) => setLimitLiters(event.target.value)}
          />
        </label>

        {!canSubmit && <p className="form-error">Лимит должен быть положительным числом.</p>}

        <button type="submit" className="primary-button full-width" disabled={!canSubmit || submitting}>
          <Send size={18} />
          {submitting ? "Сохраняем" : "Отправить"}
        </button>
      </form>
    </div>
  );
}

