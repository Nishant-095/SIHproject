export type HealthPayload = {
  status: string;
  service: string;
  version: string;
  environment: string;
};

export type ReadinessPayload = {
  status: string;
  database: string;
};

export type SystemPayload = {
  health: HealthPayload;
  readiness: ReadinessPayload;
};

export type DataClass = "SYNTHETIC" | "LIVE";

export type IndexComponent = {
  basket_item_id: string;
  origin_iata: string;
  destination_iata: string;
  advance_window: string;
  current_price: string | null;
  base_price: string | null;
  price_relative: string | null;
  configured_weight: string;
  effective_weight: string | null;
  contribution: string | null;
  availability_reason: string;
};

export type DailyIndex = {
  id: string;
  collection_run_id: string;
  methodological_date: string;
  data_class: DataClass;
  basket_version: string;
  methodology_version: string;
  canonicalization_version: string;
  index_value: string | null;
  coverage_percent: string;
  publication_status: string;
  calculated_at: string;
  components: IndexComponent[];
};

export type IndexHistoryPoint = Pick<
  DailyIndex,
  "id" | "methodological_date" | "data_class" | "index_value" | "coverage_percent" | "publication_status"
>;

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT";

export type IndexCoverage = {
  methodological_date: string;
  data_class: DataClass;
  publication_status: string;
  index_value: string | null;
  coverage_percent: string;
  source_count: number;
  confidence_level: ConfidenceLevel;
  missing_data_policy: {
    code: string;
    minimum_publication_coverage_percent: string;
    imputation: string;
    available_weight_treatment: string;
    period_value_treatment: string;
  };
  source_dispersion: { source_code: string; observation_count: number; share_percent: string }[];
  routes: {
    origin_iata: string;
    destination_iata: string;
    total_windows: number;
    available_windows: number;
    coverage_percent: string;
    configured_weight: string;
    available_weight: string;
    source_count: number;
    observation_count: number;
    missing_windows: string[];
    confidence_level: ConfidenceLevel;
  }[];
  warnings: string[];
};

export type PeriodIndex = {
  id: string;
  data_class: DataClass;
  period_type: "WEEKLY" | "MONTHLY";
  period_start: string;
  period_end: string;
  methodology_version: string;
  missing_data_policy: string;
  index_value: string | null;
  average_coverage_percent: string;
  minimum_coverage_percent: string;
  expected_day_count: number;
  observed_day_count: number;
  valued_day_count: number;
  low_coverage_day_count: number;
  source_count: number;
  confidence_level: ConfidenceLevel;
  aggregation_status: "COMPLETE" | "PARTIAL" | "INSUFFICIENT_COVERAGE" | "NO_DATA";
  warnings: string[];
  calculated_at: string;
};

export type RouteSummary = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  active: boolean;
  selection_basis: string;
};

export type RouteAnalytics = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  selection_basis: string;
  latest_route_index: string | null;
  latest_date: string | null;
  carriers: string[];
  source_dispersion: { source_code: string; observation_count: number }[];
};

export type RouteHistoryPoint = {
  methodological_date: string;
  route_index: string | null;
  average_fare: string | null;
  coverage_percent: string;
};

export type LeadTimePoint = {
  methodological_date: string;
  travel_date: string;
  advance_window: string;
  median_fare: string;
  observation_count: number;
};

export type LeadTime = {
  origin_iata: string;
  destination_iata: string;
  travel_date: string | null;
  data_class: DataClass;
  points: LeadTimePoint[];
};

export type FareObservation = {
  id: string;
  raw_quote_id: string;
  observed_at_utc: string;
  methodological_date: string;
  origin_iata: string;
  destination_iata: string;
  travel_date: string;
  advance_days: number;
  advance_window: string;
  carrier_code: string | null;
  carrier_name: string | null;
  flight_number: string | null;
  departure_time_local: string | null;
  arrival_time_local: string | null;
  is_nonstop: boolean | null;
  cabin_class: string | null;
  fare_class: string | null;
  currency: string | null;
  base_fare: string | null;
  taxes: string | null;
  udf: string | null;
  convenience_fee: string | null;
  other_fees: string | null;
  total_fare: string | null;
  availability: string;
  flight_identity_input: string | null;
  flight_identity: string | null;
  quality_status: string;
  quality_flags: string[];
  quality_score: number | null;
  included_in_index: boolean;
  exclusion_reason: string | null;
  normalization_version: string;
};

export type RawQuote = {
  id: string;
  collection_job_id: string;
  source_id: string;
  data_class: DataClass;
  observed_at_utc: string;
  query_origin: string;
  query_destination: string;
  query_travel_date: string;
  raw_airline_name: string | null;
  raw_flight_number: string | null;
  raw_departure: string | null;
  raw_arrival: string | null;
  raw_fare_text: string | null;
  raw_currency: string | null;
  raw_base_fare: string | null;
  raw_tax_text: string | null;
  raw_total_fare: string | null;
  raw_payload: Record<string, unknown>;
  parser_version: string;
  content_hash: string;
};

export type Provenance = {
  source_code: string;
  source_name: string;
  route: string;
  collection_run_id: string;
  collection_job_id: string;
  observation: FareObservation;
  raw_quote: RawQuote;
};

export type QualitySummary = {
  data_class: DataClass;
  total_observations: number;
  included_observations: number;
  excluded_observations: number;
  flagged_observations: number;
  average_quality_score: string | null;
  inclusion_rate_percent: string;
  status_counts: Record<string, number>;
  flag_counts: Record<string, number>;
};

export type CollectionRun = {
  id: string;
  methodological_date: string;
  scheduled_for_utc: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  trigger_type: string;
  data_class: DataClass;
  planned_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  valid_observations: number;
};

export type CollectionJob = {
  id: string;
  source_id: string;
  route_id: string;
  travel_date: string;
  advance_days: number;
  advance_window: string;
  status: string;
  attempt_count: number;
  failure_code: string | null;
  error_message: string | null;
};

export type CollectionRunDetail = CollectionRun & { jobs: CollectionJob[]; created: boolean | null };

export type SourceHealth = {
  source_code: string;
  source_name: string;
  enabled: boolean;
  review_status: string;
  health_status: string;
  successful_jobs: number;
  failed_jobs: number;
  success_rate: number | null;
  average_duration_ms: number | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_failure_code: string | null;
  parser_version: string;
};

export type SourceHealthHistoryPoint = {
  source_code: string;
  methodological_date: string;
  successful_jobs: number;
  failed_jobs: number;
  success_rate: number | null;
  average_duration_ms: number | null;
  health_status: string;
  parser_version: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function readJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(detail?.detail ?? (path === "/ready" ? "Database is not ready" : "Backend is unavailable"));
  }
  return (await response.json()) as T;
}

export const api = {
  currentIndex: (signal: AbortSignal) => readJson<DailyIndex>("/api/v1/index/current", signal),
  currentIndexCoverage: (signal: AbortSignal) => readJson<IndexCoverage>("/api/v1/index/current/coverage", signal),
  indexHistory: (signal: AbortSignal) => readJson<IndexHistoryPoint[]>("/api/v1/index/history", signal),
  weeklyIndex: (signal: AbortSignal) => readJson<PeriodIndex[]>("/api/v1/index/weekly", signal),
  monthlyIndex: (signal: AbortSignal) => readJson<PeriodIndex[]>("/api/v1/index/monthly", signal),
  routes: (signal: AbortSignal) => readJson<RouteSummary[]>("/api/v1/routes", signal),
  route: (origin: string, destination: string, signal: AbortSignal) =>
    readJson<RouteAnalytics>(`/api/v1/routes/${origin}/${destination}`, signal),
  routeHistory: (origin: string, destination: string, signal: AbortSignal) =>
    readJson<RouteHistoryPoint[]>(`/api/v1/routes/${origin}/${destination}/history`, signal),
  leadTime: (origin: string, destination: string, signal: AbortSignal) =>
    readJson<LeadTime>(`/api/v1/routes/${origin}/${destination}/lead-time`, signal),
  observations: (signal: AbortSignal) => readJson<FareObservation[]>("/api/v1/observations?limit=100", signal),
  provenance: (id: string, signal: AbortSignal) =>
    readJson<Provenance>(`/api/v1/observations/${id}/provenance`, signal),
  quality: (signal: AbortSignal) => readJson<QualitySummary>("/api/v1/quality/summary", signal),
  runs: (signal: AbortSignal) => readJson<CollectionRun[]>("/api/v1/collection-runs?limit=20", signal),
  run: (id: string, signal: AbortSignal) => readJson<CollectionRunDetail>(`/api/v1/collection-runs/${id}`, signal),
  sourceHealth: (signal: AbortSignal) => readJson<SourceHealth[]>("/api/v1/sources/health", signal),
  sourceHealthHistory: (signal: AbortSignal) => readJson<SourceHealthHistoryPoint[]>("/api/v1/sources/health/history", signal),
};

export async function fetchSystemStatus(signal: AbortSignal): Promise<SystemPayload> {
  const [health, readiness] = await Promise.all([
    readJson<HealthPayload>("/health", signal),
    readJson<ReadinessPayload>("/ready", signal),
  ]);
  return { health, readiness };
}
