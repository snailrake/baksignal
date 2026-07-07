import type { FuelType } from "../types/domain";
import { fuelOptions } from "../lib/status";

type FuelFilterProps = {
  value: FuelType;
  onChange: (fuelType: FuelType) => void;
};

export function FuelFilter({ value, onChange }: FuelFilterProps) {
  return (
    <div className="fuel-filter" role="tablist" aria-label="Тип топлива">
      {fuelOptions.map((option) => (
        <button
          key={option.value}
          type="button"
          className={option.value === value ? "fuel-filter__item active" : "fuel-filter__item"}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

