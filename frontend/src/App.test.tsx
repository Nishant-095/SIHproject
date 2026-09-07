import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

const index = {
  id: "index-1", collection_run_id: "run-1", methodological_date: "2026-09-05", data_class: "SYNTHETIC",
  basket_version: "mvp-v1", methodology_version: "1.0", canonicalization_version: "1.0", index_value: "103.25",
  coverage_percent: "100", publication_status: "PUBLISHED", calculated_at: "2026-09-05T06:00:00Z",
  components: [{ basket_item_id: "b-1", origin_iata: "DEL", destination_iata: "BOM", advance_window: "T_PLUS_7", current_price: "5200", base_price: "5000", price_relative: "104", configured_weight: "1", effective_weight: "1", contribution: "104", availability_reason: "AVAILABLE" }],
};

const observation = {
  id: "obs-1", raw_quote_id: "raw-1", observed_at_utc: "2026-09-05T06:00:00Z", methodological_date: "2026-09-05",
  origin_iata: "DEL", destination_iata: "BOM", travel_date: "2026-09-12", advance_days: 7, advance_window: "T_PLUS_7",
  carrier_code: "AI", carrier_name: "Air India", flight_number: "AI101", departure_time_local: "09:00:00", arrival_time_local: "11:00:00",
  is_nonstop: true, cabin_class: "ECONOMY", fare_class: "Y", currency: "INR", base_fare: "4300", taxes: "700", udf: "0",
  convenience_fee: "100", other_fees: "100", total_fare: "5200", availability: "AVAILABLE", flight_identity_input: "AI101",
  flight_identity: "AI-101", quality_status: "VALID", quality_flags: [], quality_score: 100, included_in_index: true,
  exclusion_reason: null, normalization_version: "1.0",
};

function apiMock(input: RequestInfo | URL) {
  const url = String(input);
  if (url.includes("/index/current/coverage")) return json({ methodological_date: "2026-09-05", data_class: "SYNTHETIC", publication_status: "PUBLISHED", index_value: "103.25", coverage_percent: "100", source_count: 1, confidence_level: "LOW", missing_data_policy: { code: "published-days-mean-no-imputation-v1", minimum_publication_coverage_percent: "80", imputation: "NONE", available_weight_treatment: "RENORMALIZE_TO_AVAILABLE_BASKET_WEIGHT", period_value_treatment: "MEAN_OF_PUBLISHED_DAILY_VALUES_ONLY" }, source_dispersion: [{ source_code: "FIXTURE_LOCAL", observation_count: 2, share_percent: "100" }], routes: [{ origin_iata: "DEL", destination_iata: "BOM", total_windows: 1, available_windows: 1, coverage_percent: "100", configured_weight: "1", available_weight: "1", source_count: 1, observation_count: 2, missing_windows: [], confidence_level: "LOW" }], warnings: ["SINGLE_SOURCE"] });
  if (url.includes("/index/current")) return json(index);
  if (url.includes("/index/history")) return json([{ id: "old", methodological_date: "2026-09-04", data_class: "SYNTHETIC", index_value: "100", coverage_percent: "100", publication_status: "PUBLISHED" }, { id: "new", methodological_date: "2026-09-05", data_class: "SYNTHETIC", index_value: "103.25", coverage_percent: "100", publication_status: "PUBLISHED" }]);
  if (url.includes("/index/weekly")) return json([{ id: "week-1", data_class: "SYNTHETIC", period_type: "WEEKLY", period_start: "2026-08-31", period_end: "2026-09-06", methodology_version: "1.0", missing_data_policy: "published-days-mean-no-imputation-v1", index_value: "103.25", average_coverage_percent: "100", minimum_coverage_percent: "100", expected_day_count: 7, observed_day_count: 1, valued_day_count: 1, low_coverage_day_count: 0, source_count: 1, confidence_level: "LOW", aggregation_status: "PARTIAL", warnings: ["PARTIAL_PERIOD", "SINGLE_SOURCE"], calculated_at: "2026-09-05T06:00:00Z" }]);
  if (url.includes("/index/monthly")) return json([{ id: "month-1", data_class: "SYNTHETIC", period_type: "MONTHLY", period_start: "2026-09-01", period_end: "2026-09-30", methodology_version: "1.0", missing_data_policy: "published-days-mean-no-imputation-v1", index_value: "103.25", average_coverage_percent: "100", minimum_coverage_percent: "100", expected_day_count: 30, observed_day_count: 1, valued_day_count: 1, low_coverage_day_count: 0, source_count: 1, confidence_level: "LOW", aggregation_status: "PARTIAL", warnings: ["PARTIAL_PERIOD", "SINGLE_SOURCE"], calculated_at: "2026-09-05T06:00:00Z" }]);
  if (url.match(/\/routes\/DEL\/BOM\/history/)) return json([{ methodological_date: "2026-09-04", route_index: "100", average_fare: "5000", coverage_percent: "100" }, { methodological_date: "2026-09-05", route_index: "104", average_fare: "5200", coverage_percent: "100" }]);
  if (url.match(/\/routes\/DEL\/BOM\/lead-time/)) return json({ origin_iata: "DEL", destination_iata: "BOM", travel_date: "2026-09-12", data_class: "SYNTHETIC", points: [{ methodological_date: "2026-09-05", travel_date: "2026-09-12", advance_window: "T_PLUS_7", median_fare: "5200", observation_count: 1 }] });
  if (url.match(/\/routes\/DEL\/BOM$/)) return json({ id: "route-1", origin_iata: "DEL", destination_iata: "BOM", selection_basis: "MVP", latest_route_index: "104", latest_date: "2026-09-05", carriers: ["AI"], source_dispersion: [{ source_code: "FIXTURE_LOCAL", observation_count: 2 }] });
  if (url.match(/\/routes$/)) return json([{ id: "route-1", origin_iata: "DEL", destination_iata: "BOM", active: true, selection_basis: "MVP" }]);
  if (url.includes("/observations/obs-1/provenance")) return json({ source_code: "fixture", source_name: "Fixture source", route: "DEL-BOM", collection_run_id: "run-1", collection_job_id: "job-1", observation, raw_quote: { id: "raw-1", collection_job_id: "job-1", source_id: "source-1", data_class: "SYNTHETIC", observed_at_utc: "2026-09-05T06:00:00Z", query_origin: "DEL", query_destination: "BOM", query_travel_date: "2026-09-12", raw_airline_name: "Air India", raw_flight_number: "AI101", raw_departure: null, raw_arrival: null, raw_fare_text: "INR 5,200", raw_currency: "INR", raw_base_fare: "4300", raw_tax_text: "700", raw_total_fare: "5200", raw_payload: { offer: "fixture" }, parser_version: "fixture-v1", content_hash: "abc123" } });
  if (url.includes("/observations")) return json([observation]);
  if (url.includes("/quality/summary")) return json({ data_class: "SYNTHETIC", total_observations: 1, included_observations: 1, excluded_observations: 0, flagged_observations: 0, average_quality_score: "100", inclusion_rate_percent: "100", status_counts: { VALID: 1 }, flag_counts: {} });
  if (url.includes("/sources/health/history")) return json([{ source_code: "FIXTURE_LOCAL", methodological_date: "2026-09-05", successful_jobs: 1, failed_jobs: 0, success_rate: 100, average_duration_ms: 10, health_status: "HEALTHY", parser_version: "fixture-v1" }]);
  if (url.includes("/sources/health")) return json([{ source_code: "fixture", source_name: "Fixture source", enabled: true, review_status: "APPROVED", health_status: "HEALTHY", successful_jobs: 1, failed_jobs: 0, success_rate: 100, average_duration_ms: 10, last_success_at: "2026-09-05T06:00:00Z", last_failure_at: null, last_failure_code: null, parser_version: "fixture-v1" }]);
  if (url.match(/\/collection-runs\/run-1$/)) return json({ id: "run-1", methodological_date: "2026-09-05", scheduled_for_utc: "2026-09-05T05:30:00Z", started_at: "2026-09-05T05:30:00Z", finished_at: "2026-09-05T06:00:00Z", status: "COMPLETED", trigger_type: "MANUAL", data_class: "SYNTHETIC", planned_jobs: 1, successful_jobs: 1, failed_jobs: 0, valid_observations: 1, created: true, jobs: [{ id: "job-1", source_id: "source-1", route_id: "route-1", travel_date: "2026-09-12", advance_days: 7, advance_window: "T_PLUS_7", status: "SUCCEEDED", attempt_count: 1, failure_code: null, error_message: null }] });
  if (url.includes("/collection-runs")) return json([{ id: "run-1", methodological_date: "2026-09-05", scheduled_for_utc: "2026-09-05T05:30:00Z", started_at: "2026-09-05T05:30:00Z", finished_at: "2026-09-05T06:00:00Z", status: "COMPLETED", trigger_type: "MANUAL", data_class: "SYNTHETIC", planned_jobs: 1, successful_jobs: 1, failed_jobs: 0, valid_observations: 1 }]);
  return json({ detail: "not mocked" }, 404);
}

describe("Airfare APIx analytics console", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("renders the APIx overview from public API data", async () => {
    vi.stubGlobal("fetch", vi.fn(apiMock));
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByText("Loading verified API data")).toBeInTheDocument();
    expect((await screen.findAllByText("103.25"))[0]).toBeInTheDocument();
    expect(screen.getByText("Route and advance-window matrix")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Weekly and monthly aggregation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Coverage confidence: LOW" })).toBeInTheDocument();
    expect(screen.getByText("Single source")).toBeInTheDocument();
    expect(screen.getAllByText("SYNTHETIC").length).toBeGreaterThan(0);
  });

  it("renders route history and lead-time context", async () => {
    vi.stubGlobal("fetch", vi.fn(apiMock));
    render(<MemoryRouter initialEntries={["/routes"]}><App /></MemoryRouter>);
    expect(await screen.findByText("Current route index")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lead-time curve" })).toBeInTheDocument();
    expect(screen.getAllByText("AI")[0]).toBeInTheDocument();
  });

  it("shows preserved raw and normalized provenance", async () => {
    vi.stubGlobal("fetch", vi.fn(apiMock));
    render(<MemoryRouter initialEntries={["/provenance"]}><App /></MemoryRouter>);
    expect(await screen.findByText("Included in index")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Raw quote" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("View preserved raw payload"));
    expect(screen.getAllByText(/fixture/)[0]).toBeInTheDocument();
  });

  it("shows latest jobs, source health, and quality outcomes", async () => {
    vi.stubGlobal("fetch", vi.fn(apiMock));
    render(<MemoryRouter initialEntries={["/operations"]}><App /></MemoryRouter>);
    expect(await screen.findByText("No degraded, blocked, or parser-change source alerts.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Latest collection jobs" })).toBeInTheDocument();
    expect(await screen.findByText("SUCCEEDED")).toBeInTheDocument();
    expect(screen.getByText("HEALTHY")).toBeInTheDocument();
  });

  it("keeps API failure visible and retries", async () => {
    const fetchMock = vi.fn().mockImplementationOnce(() => json({ detail: "Database unavailable" }, 503)).mockImplementation(apiMock);
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect((await screen.findAllByText("103.25"))[0]).toBeInTheDocument();
  });
});
