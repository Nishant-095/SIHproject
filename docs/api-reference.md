# Airfare APIx API Reference

**Implemented base URL:** `http://localhost:8000`  
**API prefix:** `/api/v1`  
**Interactive schema:** `/docs`  
**OpenAPI JSON:** `/openapi.json`

The generated OpenAPI document is the field-level source of truth. This guide
groups the endpoints by user job and gives commands that can be run against the
local Docker environment.

## Conventions

- JSON is returned unless the route is an explicit CSV or Excel download.
- UUIDs are lowercase strings in responses.
- Dates use `YYYY-MM-DD`; timestamps use ISO 8601.
- Money and index values are serialized as exact decimal-compatible values.
- IATA path/query values are three-letter airport codes.
- List endpoints may return `[]`; missing single resources return `404`.
- Invalid input returns FastAPI's `422` validation response.
- A state conflict or disabled/unapproved source returns `409`.

### Data classes

| Value | Meaning |
|---|---|
| `LIVE` | Obtained by the running system from an approved production source. |
| `HISTORICAL` | Imported from a named external reference dataset. |
| `SYNTHETIC` | Invented fixture/test evidence. Default for analytical reads. |
| `RECORDED_DEMO` | Permitted recorded source-shaped demonstration evidence. |

Never omit `data_class` when the distinction matters to a report, even where
the safe local default is `SYNTHETIC`.

### Administrative authentication

Mutation routes require the `X-Admin-Token` header:

```bash
export APIX_BASE_URL=http://localhost:8000
export APIX_ADMIN_TOKEN=replace-with-your-local-admin-token

curl -fsS -X POST "$APIX_BASE_URL/api/v1/admin/index/aggregate?data_class=SYNTHETIC" \
  -H "X-Admin-Token: $APIX_ADMIN_TOKEN"
```

The MVP token is appropriate only behind TLS and a private administrative
boundary. Do not place it in the React application or commit it to source.

## Service readiness

| Method and path | Purpose |
|---|---|
| `GET /health` | Process liveness; does not prove PostgreSQL is reachable. |
| `GET /ready` | Readiness including a database connectivity check. |

```bash
curl -fsS "$APIX_BASE_URL/health"
curl -fsS "$APIX_BASE_URL/ready"
```

## Basket and route analytics

| Method and path | Parameters | Result |
|---|---|---|
| `GET /api/v1/routes` | none | Active frozen routes. |
| `GET /api/v1/routes/{origin}/{destination}` | `data_class` | Current route summary, carriers, and source dispersion. |
| `GET /api/v1/routes/{origin}/{destination}/history` | `data_class` | Route index/fare history. |
| `GET /api/v1/routes/{origin}/{destination}/lead-time` | `data_class`, optional `travel_date` | Median fares across advance windows. |

```bash
curl -fsS "$APIX_BASE_URL/api/v1/routes"
curl -fsS "$APIX_BASE_URL/api/v1/routes/DEL/BOM?data_class=SYNTHETIC"
curl -fsS "$APIX_BASE_URL/api/v1/routes/DEL/BOM/history?data_class=SYNTHETIC"
curl -fsS "$APIX_BASE_URL/api/v1/routes/DEL/BOM/lead-time?data_class=SYNTHETIC"
```

## Observations and provenance

| Method and path | Parameters | Result |
|---|---|---|
| `GET /api/v1/observations` | `data_class`; optional `origin`, `destination`, `quality_status`, `included_in_index`, `limit` (1–500), `offset` | Filtered normalized observations. |
| `GET /api/v1/observations/{observation_id}` | path UUID | One normalized observation. |
| `GET /api/v1/observations/{observation_id}/provenance` | path UUID | Source, run, job, raw quote, and normalized record. |

Quality status is one of `ELIGIBLE`, `ELIGIBLE_FLAGGED`, `EXCLUDED`, or
`MANUAL_REVIEW`.

```bash
curl -fsS "$APIX_BASE_URL/api/v1/observations?data_class=SYNTHETIC&origin=DEL&included_in_index=true&limit=20"

OBSERVATION_ID=replace-with-an-observation-uuid
curl -fsS "$APIX_BASE_URL/api/v1/observations/$OBSERVATION_ID/provenance"
```

## Collection runs

| Method and path | Parameters/body | Result |
|---|---|---|
| `GET /api/v1/collection-runs` | `limit` 1–200, default 50 | Recent collection runs. |
| `GET /api/v1/collection-runs/{run_id}` | path UUID | Run plus its jobs. |
| `POST /api/v1/admin/collection-runs` | JSON source/date | Run the selected adapter. |
| `POST /api/v1/admin/collection-runs/fixture` | optional `methodological_date` | Run fixture collection. |
| `POST /api/v1/admin/collection-runs/duffel` | optional `methodological_date` | Run configured Duffel collection. |
| `POST /api/v1/admin/collection-runs/permissioned-web` | optional `methodological_date` | Run configured permissioned browser source. |

```bash
curl -fsS "$APIX_BASE_URL/api/v1/collection-runs?limit=10"

curl -fsS -X POST "$APIX_BASE_URL/api/v1/admin/collection-runs" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $APIX_ADMIN_TOKEN" \
  -d '{"source":"fixture","methodological_date":"2098-12-09"}'
```

Valid body sources are `fixture`, `duffel`, and `permissioned-web`. A real
adapter refuses to run until its enablement, approval, and credential or
permission settings are all satisfied.

## APIx and aggregates

| Method and path | Parameters | Result |
|---|---|---|
| `GET /api/v1/index/current` | `data_class` | Latest daily APIx with components and versions. |
| `GET /api/v1/index/current/coverage` | `data_class` | Basket, route, source, warning, and confidence evidence. |
| `GET /api/v1/index/history` | `data_class`, `limit` 1–366 | Chronological daily series. |
| `GET /api/v1/index/daily/{date}` | `data_class` | One methodological date. |
| `GET /api/v1/index/weekly` | `data_class`, `limit` 1–104 | Weekly aggregates. |
| `GET /api/v1/index/monthly` | `data_class`, `limit` 1–60 | Monthly aggregates. |
| `POST /api/v1/admin/index/recalculate` | required `run_id` | Recalculate a run's daily index. |
| `POST /api/v1/admin/index/aggregate` | `data_class` | Refresh weekly/monthly rows. |

```bash
curl -fsS "$APIX_BASE_URL/api/v1/index/current?data_class=SYNTHETIC"
curl -fsS "$APIX_BASE_URL/api/v1/index/current/coverage?data_class=SYNTHETIC"
curl -fsS "$APIX_BASE_URL/api/v1/index/history?data_class=SYNTHETIC&limit=30"

RUN_ID=replace-with-a-collection-run-uuid
curl -fsS -X POST "$APIX_BASE_URL/api/v1/admin/index/recalculate?run_id=$RUN_ID" \
  -H "X-Admin-Token: $APIX_ADMIN_TOKEN"
```

An index may legitimately have no `index_value` while its base is provisional
or coverage is below the publication rule. Inspect `publication_status`,
`coverage_percent`, warnings, and component lineage instead of treating null as
zero.

## Quality and source health

| Method and path | Parameters | Result |
|---|---|---|
| `GET /api/v1/quality/summary` | `data_class` | Counts and quality/inclusion summary. |
| `GET /api/v1/sources/health` | none | Current source state and recent reliability. |
| `GET /api/v1/sources/health/history` | `limit_days` 1–90 | Daily source-health history. |
| `POST /api/v1/admin/sources/{source_id}/enable` | path UUID | Enable an approved source. |
| `POST /api/v1/admin/sources/{source_id}/disable` | path UUID | Disable a source. |

Legacy aliases `/api/v1/sources/{source_id}/enable|disable` remain available
with the same admin-token protection; new clients should use `/admin/sources`.

```bash
curl -fsS "$APIX_BASE_URL/api/v1/quality/summary?data_class=SYNTHETIC"
curl -fsS "$APIX_BASE_URL/api/v1/sources/health"
curl -fsS "$APIX_BASE_URL/api/v1/sources/health/history?limit_days=30"
```

## Historical reference and back-test

| Method and path | Parameters/body | Result |
|---|---|---|
| `GET /api/v1/historical/datasets` | none | Dataset metadata list. |
| `GET /api/v1/historical/datasets/{dataset_code}` | path code | Metadata and observations. |
| `POST /api/v1/admin/historical/datasets` | provenance metadata plus observations | Idempotent import. |
| `GET /api/v1/historical/backtest` | required `dataset_code`, `data_class` | Rebased monthly comparison and coverage. |

```bash
DATASET_CODE=MOSPI-AIRFARE-CPI-2012-2025-10-SAMPLE
curl -fsS "$APIX_BASE_URL/api/v1/historical/datasets/$DATASET_CODE"
curl -fsS "$APIX_BASE_URL/api/v1/historical/backtest?dataset_code=$DATASET_CODE&data_class=SYNTHETIC"
```

The import request schema, including each historical observation field, is
kept current at `/docs`; the supported CSV import command is documented in the
project README.

## Exports

| Method and path | Required/optional query | Format |
|---|---|---|
| `GET /api/v1/exports/fare-observations.csv` | `data_class` | CSV |
| `GET /api/v1/exports/index.csv` | `data_class` | CSV |
| `GET /api/v1/exports/period-index.csv` | `data_class` | CSV |
| `GET /api/v1/exports/backtest.csv` | required `dataset_code`, `data_class` | CSV |
| `GET /api/v1/exports/package.json` | `data_class`, optional `dataset_code` | JSON |
| `GET /api/v1/exports/analysis.xlsx` | `data_class`, optional `dataset_code` | XLSX |

```bash
curl -fsS -o apix-synthetic.csv \
  "$APIX_BASE_URL/api/v1/exports/index.csv?data_class=SYNTHETIC"

curl -fsS -o airfare-analysis.xlsx \
  "$APIX_BASE_URL/api/v1/exports/analysis.xlsx?data_class=SYNTHETIC&dataset_code=$DATASET_CODE"
```

Exports include the applicable data class, generation time, methodology and
missing-data metadata, and relational evidence identifiers. They do not merge
synthetic and live series.

