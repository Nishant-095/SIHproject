# SIH26056 Airfare APIx — MVP Data Dictionary

**Status:** Phase 0 contract with implemented Phase 1–15 extensions  
**Schema contract version:** `schema-contract-v0.5.0`  
**Effective date:** 2026-09-05

## 1. Conventions

- Primary keys are UUIDs unless implementation evidence justifies another
  stable identifier.
- Event timestamps use timezone-aware UTC database values.
- Airport-service and travel dates use `date`.
- Money uses PostgreSQL `numeric`, never binary floating point.
- Currency uses ISO 4217 code and is `INR` for eligible MVP observations.
- Raw evidence is append-only during normal operation.
- Derived rows keep input identifiers and processing-policy versions.
- JSON is used for compact source evidence and component snapshots, not as a
  replacement for important relational keys.

## 2. Core relationships

```text
source 1---* collection_job *---1 collection_run
route  1---* collection_job
collection_job 1---* raw_quote
raw_quote 1---0..1 fare_observation
fare_observation *---* canonical_fare (through canonical_fare_observations)
canonical_fare *---* daily_route_window_price (through route_window_price_inputs)
daily_route_window_price *---1 daily_index_component
daily_index_component *---1 daily_index
daily_index *---* period_index (through period_index_inputs)
basket_version 1---* basket_item
historical_dataset 1---* historical_index_observation
```

## 3. Enumerations

### `source_type`

```text
AIRLINE_DIRECT
OTA
PUBLIC_DATA
FIXTURE
```

### `source_review_status`

```text
PENDING_REVIEW
APPROVED
RESTRICTED
BLOCKED
PARSER_CHANGED
DISABLED
```

### `data_class`

```text
LIVE
HISTORICAL
SYNTHETIC
RECORDED_DEMO
```

### `advance_window`

```text
T1
T7
T15
T30
T45
OTHER
```

### `run_trigger`

```text
SCHEDULED
MANUAL
BACKFILL
TEST
```

### `job_status`

```text
PLANNED
RUNNING
SUCCEEDED
FAILED
SKIPPED
```

### `availability_status`

```text
AVAILABLE
SOLD_OUT
CANCELLED
NO_RESULT
SOURCE_FAILURE
UNKNOWN
```

### `quality_status`

```text
ELIGIBLE
ELIGIBLE_FLAGGED
EXCLUDED
MANUAL_REVIEW
```

### `quality_flag`

```text
DUPLICATE
SOURCE_CONFLICT
FARE_COMPONENT_MISMATCH
POSSIBLE_OUTLIER
MISSING_FARE
PARSER_ERROR
UNSUPPORTED_CURRENCY
UNSUPPORTED_CABIN
CONNECTING_FLIGHT
INCOMPLETE_FLIGHT_IDENTITY
UNAPPROVED_SOURCE
UNKNOWN_AIRPORT
ROUTE_MISMATCH
NEGATIVE_FARE
UNAVAILABLE_FARE
INVALID_TRAVEL_DATE
INVALID_BOOKING_WINDOW
DATA_CLASS_MISMATCH
SOURCE_MISMATCH
MANUAL_REVIEW
```

### `failure_code`

```text
SOURCE_UNAVAILABLE
RATE_LIMITED
ROBOTS_DISALLOWED
TERMS_RESTRICTED
CAPTCHA_BLOCKED
AUTHENTICATION_FAILED
PARSER_CHANGED
NO_RESULTS
NETWORK_TIMEOUT
INVALID_RESPONSE
UNKNOWN_ERROR
```

### `publication_status`

```text
PUBLISHED
INSUFFICIENT_COVERAGE
PROVISIONAL_BASE
FAILED
```

### `aggregation_period`, `aggregation_status`, and `confidence_level`

```text
aggregation_period: WEEKLY | MONTHLY
aggregation_status: COMPLETE | PARTIAL | INSUFFICIENT_COVERAGE | NO_DATA
confidence_level: HIGH | MEDIUM | LOW | INSUFFICIENT
```

## 4. `sources`

One configured collection source.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `code` | varchar | Unique stable code |
| `name` | varchar | Display name |
| `source_type` | enum | Direct airline, OTA, public data, or fixture |
| `base_url` | varchar nullable | No credentials in URL |
| `enabled` | boolean | Scheduler switch |
| `collection_method` | varchar | API, HTTP, browser, fixture, or import |
| `review_status` | enum | Only `APPROVED` can produce eligible live data |
| `reviewed_at` | timestamptz nullable | Current terms-review time |
| `rate_limit_per_minute` | integer nullable | Approved maximum |
| `max_concurrency` | integer | MVP default 1 |
| `parser_version` | varchar | Current adapter parser version |
| `created_at` | timestamptz | Audit timestamp |
| `updated_at` | timestamptz | Audit timestamp |

## 5. `routes`

One directed airport pair in the basket.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `origin_iata` | char(3) | Uppercase IATA code |
| `destination_iata` | char(3) | Uppercase IATA code, different from origin |
| `active` | boolean | Planner includes active routes |
| `selection_basis` | text | Why the route is included |
| `created_at` | timestamptz | Audit timestamp |

Unique constraint: `(origin_iata, destination_iata)`.

Phase 0 seed routes are `DEL-BOM`, `DEL-BLR`, and `BOM-BLR`.

## 6. `collection_runs`

One planned collection cycle.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `methodological_date` | date | Asia/Kolkata scheduled observation date |
| `scheduled_for_utc` | timestamptz | 10:00 IST converted to UTC |
| `started_at` | timestamptz nullable | Actual start |
| `finished_at` | timestamptz nullable | Actual end |
| `status` | varchar | Planned/running/completed/partial/failed |
| `trigger_type` | enum | Scheduled, manual, backfill, or test |
| `data_class` | enum | Cannot mix classes in one run |
| `planned_jobs` | integer | Non-negative |
| `successful_jobs` | integer | Non-negative |
| `failed_jobs` | integer | Non-negative |
| `valid_observations` | integer | Non-negative |
| `created_at` | timestamptz | Audit timestamp |

Unique idempotency constraint: `(methodological_date, scheduled_for_utc,
trigger_type, data_class)` for ordinary scheduled operation.

## 7. `collection_jobs`

One source-route-window query inside a run.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `collection_run_id` | UUID | Foreign key to run |
| `source_id` | UUID | Foreign key to source |
| `route_id` | UUID | Foreign key to route |
| `travel_date` | date | Planner-calculated date |
| `advance_days` | integer | Exact date difference |
| `advance_window` | enum | T1/T7/T15/T30/T45 for MVP jobs |
| `status` | enum | Job lifecycle |
| `attempt_count` | integer | Starts at 0; bounded retries |
| `started_at` | timestamptz nullable | Actual start |
| `finished_at` | timestamptz nullable | Actual finish |
| `failure_code` | enum nullable | Structured failure |
| `error_message` | text nullable | Sanitized diagnostic; no secrets |
| `idempotency_key` | varchar | Unique deterministic key |
| `created_at` | timestamptz | Audit timestamp |

Unique constraint: `idempotency_key`.

## 8. `raw_quotes`

Source evidence before common normalization.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `collection_job_id` | UUID | Foreign key to job |
| `source_id` | UUID | Denormalized audit key to source |
| `data_class` | enum | Must match run class |
| `observed_at_utc` | timestamptz | Actual source observation time |
| `query_origin` | varchar | Original query value |
| `query_destination` | varchar | Original query value |
| `query_travel_date` | date | Original query value |
| `raw_airline_name` | text nullable | Unmodified source value |
| `raw_flight_number` | text nullable | Unmodified source value |
| `raw_departure` | text nullable | Unmodified source value |
| `raw_arrival` | text nullable | Unmodified source value |
| `raw_fare_text` | text nullable | Unmodified displayed fare |
| `raw_currency` | char(3) nullable | Unmodified source currency code |
| `raw_base_fare` | numeric nullable | Source value when structured |
| `raw_tax_text` | text nullable | Unmodified source value |
| `raw_total_fare` | numeric nullable | Source value when structured |
| `raw_payload` | jsonb | Minimal permitted source-shaped evidence |
| `parser_version` | varchar | Parser used to create this record |
| `content_hash` | char(64) | SHA-256 of canonical retained evidence |
| `created_at` | timestamptz | Insert time |

Raw records are not updated in normal processing. Corrections occur in derived
rows with a new processing version.

## 9. `fare_observations`

Normalized, source-specific interpretation of one raw quote.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `raw_quote_id` | UUID | Unique foreign key to raw quote |
| `observed_at_utc` | timestamptz | Copied semantic event time |
| `methodological_date` | date | Asia/Kolkata collection date |
| `origin_iata` | char(3) | Normalized origin |
| `destination_iata` | char(3) | Normalized destination |
| `travel_date` | date | Airport-service date |
| `advance_days` | integer | Exact difference |
| `advance_window` | enum | Normalized window |
| `carrier_code` | varchar nullable | Normalized carrier |
| `carrier_name` | varchar nullable | Normalized display name |
| `flight_number` | varchar nullable | Normalized flight number |
| `departure_time_local` | time nullable | Scheduled local time |
| `arrival_time_local` | time nullable | Scheduled local time |
| `is_nonstop` | boolean nullable | Eligibility input |
| `cabin_class` | varchar nullable | Must be economy for MVP |
| `fare_class` | varchar nullable | Source fare family/class |
| `currency` | char(3) nullable | INR required for MVP |
| `base_fare` | numeric nullable | Non-negative |
| `taxes` | numeric nullable | Non-negative |
| `udf` | numeric nullable | User Development Fee if separately exposed |
| `convenience_fee` | numeric nullable | Mandatory source-known fee only |
| `other_fees` | numeric nullable | Mandatory source-known fees |
| `total_fare` | numeric nullable | Required and positive for eligibility |
| `availability` | enum | Separate from collection failure |
| `flight_identity_input` | text nullable | Reproducible canonical string |
| `flight_identity` | char(64) nullable | SHA-256 identity hash |
| `quality_status` | enum | Eligibility result |
| `quality_flags` | jsonb | Array of enumerated flags and details |
| `quality_score` | integer nullable | 0–100 operational metadata |
| `included_in_index` | boolean | Explicit decision |
| `exclusion_reason` | text nullable | Required when excluded |
| `normalization_version` | varchar | Deterministic rules version |
| `created_at` | timestamptz | Derived-row creation time |

Money check: when all components are available, their documented sum must
agree with `total_fare` within the configured decimal tolerance or receive a
fare-component flag.

## 10. `canonical_fares`

One deterministic cross-source fare per run, route/window, physical flight,
and fare specification. This is not yet a route-window price or APIx result.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `collection_run_id` | UUID | Foreign key to the class-separated run |
| `flight_identity` | char(64) | Physical-flight key |
| `route_id` | UUID | Foreign key to route |
| `advance_window` | enum | Basket dimension |
| `cabin_class` | varchar | Comparable cabin specification |
| `fare_class` | varchar | Comparable public fare specification |
| `currency` | char(3) | INR for MVP |
| `representative_total_fare` | numeric | Direct-airline median when available; otherwise approved-source median |
| `minimum_total_fare` | numeric | Minimum source representative |
| `maximum_total_fare` | numeric | Maximum source representative |
| `dispersion_amount` | numeric | Maximum minus minimum |
| `source_count` | integer | Distinct represented sources |
| `observation_count` | integer | Non-duplicate eligible candidates |
| `has_source_conflict` | boolean | True when source representatives differ |
| `selection_reason` | varchar | Direct-airline or approved-source median |
| `method_version` | varchar | `direct-then-median-v1` initially |
| `created_at` | timestamptz | Calculation time |

Unique constraint: `(collection_run_id, route_id, advance_window,
flight_identity, cabin_class, fare_class, currency)`.

## 11. `canonical_fare_observations`

A small provenance link between a canonical fare and every source observation
considered for it.

| Field | Type | Rule |
|---|---|---|
| `canonical_fare_id` | UUID | Foreign key to canonical fare |
| `observation_id` | UUID | Unique foreign key to normalized observation |
| `source_id` | UUID | Foreign key to source |
| `source_total_fare` | numeric nullable | Audited source total |
| `role` | varchar | `USED_DIRECT`, `USED_MEDIAN`, `CONSIDERED_NOT_SELECTED`, `SOURCE_CANDIDATE`, `DUPLICATE`, or `REJECTED_UNAPPROVED` |

Composite primary key: `(canonical_fare_id, observation_id)`.

This link table is required because a median can use several observations and
JSON identifiers alone would not enforce referential integrity.

The runtime `CANONICAL_FARE_POLICY` selects either
`direct-then-median-v1` or `approved-source-median-v1`; the selected value is
stored as `method_version` so the decision remains reproducible.

## 11A. Phase 7 operational QA views

`GET /api/v1/sources/health` derives, per configured source, successful and
failed job counts, success rate, average duration, last success/failure,
structured failure code, parser version, review status, and one of `HEALTHY`,
`DEGRADED`, `BLOCKED`, `PARSER_CHANGED`, or `DISABLED`.

The `possible-outlier-mad-v1` rule groups eligible observations by route and
advance window. With at least five comparable positive prices, it applies a
median absolute deviation threshold and adds `POSSIBLE_OUTLIER`, changes the
status to `ELIGIBLE_FLAGGED`, and lowers the quality score. It does not delete
the observation or remove its provenance.

## 12. `basket_versions`

A frozen index basket and base-period definition.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `version` | varchar | Unique human-readable version |
| `name` | varchar | Display name |
| `data_class` | enum | Prevents live/demo base mixing |
| `base_policy` | varchar | Seven eligible scheduled dates for live MVP |
| `base_start_date` | date nullable | Set when base construction begins |
| `base_end_date` | date nullable | Set when seven dates are frozen |
| `active` | boolean | One active version per compatible series |
| `created_at` | timestamptz | Audit timestamp |

## 13. `basket_items`

One route-window item and its fixed weight/base.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `basket_version_id` | UUID | Foreign key to basket version |
| `route_id` | UUID | Foreign key to route |
| `advance_window` | enum | T1/T7/T15/T30/T45 |
| `weight` | numeric | Positive; Phase 0 value 1/15 |
| `base_price` | numeric nullable | Frozen after base qualification |
| `base_component_ids` | jsonb | Seven daily price IDs for audit |
| `created_at` | timestamptz | Audit timestamp |

Unique constraint: `(basket_version_id, route_id, advance_window)`.

## 14. `daily_route_window_prices`

Robust daily basket-item price.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `collection_run_id` | UUID | Exact run that owns this daily aggregate |
| `methodological_date` | date | Aggregation date |
| `data_class` | enum | Series separation |
| `basket_item_id` | UUID | Foreign key to item |
| `price` | numeric nullable | Median canonical fare |
| `eligible_flight_count` | integer | Number of canonical fares used |
| `status` | varchar | Available or missing with reason |
| `aggregation_version` | varchar | Median policy version |
| `created_at` | timestamptz | Calculation time |

Unique constraint: `(methodological_date, data_class, basket_item_id,
aggregation_version)`.

## 15. `route_window_price_inputs`

A provenance link between a route-window median and each canonical physical
flight fare used to calculate it.

| Field | Type | Rule |
|---|---|---|
| `daily_route_window_price_id` | UUID | Foreign key to daily route-window price |
| `canonical_fare_id` | UUID | Foreign key to canonical fare |

Composite primary key: `(daily_route_window_price_id, canonical_fare_id)`.

## 16. `daily_indices`

One persisted overall prototype APIx result.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `collection_run_id` | UUID | Exact completed/partial run used |
| `methodological_date` | date | Index date |
| `data_class` | enum | Live/demo/test series separation |
| `basket_version_id` | UUID | Foreign key to basket version |
| `methodology_version` | varchar | `prototype-v0.1.0` initially |
| `canonicalization_version` | varchar | Upstream representative policy used |
| `index_value` | numeric nullable | Full-precision result |
| `coverage_percent` | numeric | 0–100 |
| `publication_status` | enum | Coverage/base gate result |
| `calculated_at` | timestamptz | Calculation event time |

Unique constraint: `(methodological_date, data_class, basket_version_id,
methodology_version)`.

## 17. `daily_index_components`

One reproducible contribution to a daily index.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `daily_index_id` | UUID | Foreign key to daily index |
| `basket_item_id` | UUID | Foreign key to item |
| `daily_route_window_price_id` | UUID nullable | Null only when item is missing |
| `current_price` | numeric nullable | Daily item price |
| `base_price` | numeric nullable | Frozen base used |
| `price_relative` | numeric nullable | `100 * current/base` |
| `configured_weight` | numeric | Fixed basket weight |
| `effective_weight` | numeric nullable | Weight after availability renormalization |
| `contribution` | numeric nullable | Effective weighted contribution |
| `availability_reason` | varchar | Available or exact missing reason |

Unique constraint: `(daily_index_id, basket_item_id)`.

## 18. `period_indices`

One persisted weekly or monthly APIx result under
`published-days-mean-no-imputation-v1`.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `data_class` | enum | Series separation |
| `basket_version_id` | UUID | Foreign key to the frozen basket |
| `period_type` | enum | `WEEKLY` or `MONTHLY` |
| `period_start`, `period_end` | date | Inclusive calendar bounds |
| `methodology_version` | varchar | Daily methodology used |
| `missing_data_policy` | varchar | Explicit aggregation policy version |
| `index_value` | numeric nullable | Mean of published daily values only |
| `average_coverage_percent` | numeric | Mean coverage across observed daily rows |
| `minimum_coverage_percent` | numeric | Lowest observed daily coverage |
| `expected_day_count` | integer | Seven or calendar-month length |
| `observed_day_count` | integer | Daily rows retained for the period |
| `valued_day_count` | integer | Published daily values used in the mean |
| `low_coverage_day_count` | integer | Observed rows below the publication rule |
| `source_count` | integer | Distinct source lineage across observed days |
| `confidence_level` | enum | `HIGH`, `MEDIUM`, `LOW`, or `INSUFFICIENT` |
| `aggregation_status` | enum | `COMPLETE`, `PARTIAL`, `INSUFFICIENT_COVERAGE`, or `NO_DATA` |
| `warnings` | jsonb | Explicit machine-readable warning codes |
| `calculated_at` | timestamptz | Latest refresh time |

Unique constraint: `(data_class, basket_version_id, period_type, period_start,
methodology_version)`.

## 19. `period_index_inputs`

Relational lineage between a period aggregate and every observed daily index,
including daily rows excluded from the period value.

| Field | Type | Rule |
|---|---|---|
| `period_index_id` | UUID | Foreign key to period index; cascade on derived-row deletion |
| `daily_index_id` | UUID | Foreign key to retained daily index |

Composite primary key: `(period_index_id, daily_index_id)`.

## 20. `historical_datasets`

One immutable imported reference dataset. Important fields are the unique
`code`, publisher, source URL, licence, metric, frequency, base period,
`HISTORICAL` data class, SHA-256 content hash, row count, notes, and import
timestamp. Reusing a code with different content is rejected.

## 21. `historical_index_observations`

One national or route reference value with inclusive period dates, optional
route, non-negative index value, optional 0–100 coverage, final/provisional
status, source record ID, and raw record metadata. National rows cannot contain
route codes; route rows require both codes.

## 22. Minimum indexes

Implementation must begin with indexes supporting the expected access paths:

```text
raw_quotes(observed_at_utc)
fare_observations(methodological_date)
fare_observations(origin_iata, destination_iata, travel_date)
fare_observations(advance_window)
fare_observations(flight_identity)
fare_observations(included_in_index)
collection_jobs(collection_run_id, status)
canonical_fares(collection_run_id, route_id, advance_window)
daily_indices(methodological_date, data_class)
period_indices(period_type, period_start)
historical_datasets(code)
historical_index_observations(dataset_id, period_start, scope_type)
```

Additional composite indexes require an observed query pattern; they are not
added speculatively.

## 23. Integrity rules

- Origin and destination must differ.
- Fare components cannot be negative.
- Eligible total fare must be positive and in INR.
- `advance_days` must match the two stored dates.
- `included_in_index = false` requires an exclusion reason.
- Raw, normalized, canonical, and aggregate rows retain their version fields.
- Deleting a source, route, job, or raw quote with dependent provenance is
  prohibited in ordinary application flows.
- A recalculation writes a versioned result; it never silently overwrites a
  result produced by a different methodology version.
