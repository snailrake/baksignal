export type FuelType = "92" | "95" | "dt";
export type Availability = "yes" | "no" | "unknown";
export type QueueLevel = "none" | "small" | "medium" | "large" | "unknown";
export type SourceType = "user" | "admin" | "public_news" | "imported";
export type StationVerificationStatus = "active" | "needs_review" | "hidden" | "closed";

export type StationStatus = {
  fuel_type: FuelType;
  availability: Availability;
  queue_level: QueueLevel;
  source_type: SourceType;
  confidence: number;
  observation_id: number;
  observed_at: string;
  expires_at: string;
};

export type Station = {
  id: number;
  name: string;
  brand: string | null;
  address: string;
  district: string | null;
  lat: string;
  lon: string;
  source: string;
  external_id: string | null;
  verification_status: StationVerificationStatus;
  quality_score: number;
  last_verified_at: string | null;
  statuses: StationStatus[];
};

export type ObservationPayload = {
  station_id: number;
  fuel_type: FuelType;
  availability: Availability;
  queue_level: QueueLevel;
  limit_liters: number | null;
  source_type: SourceType;
};
