# Airfare APIx

Lean Level-A implementation of SIH26056: an auditable Indian airfare collection
and prototype price-index pipeline.

Current implementation status:

- Phase 0: project contract complete;
- Phase 1: React/FastAPI/PostgreSQL Docker foundation, running locally;
- Phase 2: raw and normalized provenance storage;
- Phase 3: fixture adapter and end-to-end synthetic collection;
- Phase 4: Duffel plus a permission-gated Playwright extraction engine are
  implemented; one genuine provider call still needs an approved credential or
  written source permission;
- Phases 5–7: five-window planning, reliable workers, normalization, QA,
  outlier flags, canonical fares, and source-health reporting complete;
- Phase 8: deterministic fixed-weight APIx calculation, seven-date base,
  coverage rules, component lineage, and PostgreSQL persistence complete.
- Phase 9: complete public FastAPI/OpenAPI surface, protected administration,
  quality summaries, time series, lead-time curves, and CSV exports;
- Phase 10: four-page React dashboard for overview, routes, provenance, and
  operations, verified against local PostgreSQL-backed APIs;
- Phase 11: fixture, Duffel, and permissioned-browser adapters satisfy one
  shared request/quote contract without changes to the core pipeline;
- Phase 12: current and historical source health plus persistent in-app alerts.
- Phase 13: persisted weekly/monthly APIx, route coverage, source dispersion,
  explicit missing-data rules, confidence labels, warnings, and lineage.
- Phase 14: provenance-aware historical imports, monthly rebased comparison,
  deviation, coverage, route-level analysis, and a 30-day back-test pathway;
- Phase 15: CSV, JSON, and six-sheet Excel exports with methodology and
  provenance metadata.
- Phase 16: product context, full API reference/examples, Azure production
  procedure, final acceptance record, and dashboard baseline evidence.
- Post-roadmap frontend: premium Flight Recorder / Index Exchange visual system,
  self-hosted typography, GSAP route/chart motion, accessible chart evidence,
  and responsive desktop/tablet/mobile layouts.

The original 16-phase roadmap and evidence-based completion status are tracked
in [`docs/master-phase-status.md`](docs/master-phase-status.md).

Genuine credentialed source collection is not claimed here. APIx and the
dashboard are currently verified with synthetic/fixture data; a
genuine `LIVE` series still depends on the Phase 4 credential/permission gate.

## Documentation map

- [`PRODUCT.md`](PRODUCT.md) — audience, product truth, constraints, and success
  criteria;
- [`docs/architecture.md`](docs/architecture.md) — modular-monolith and lineage
  contract;
- [`docs/methodology.md`](docs/methodology.md) — basket, fare definition, base,
  formula, coverage, and limitations;
- [`docs/data-dictionary.md`](docs/data-dictionary.md) — persisted entities and
  fields;
- [`docs/api-reference.md`](docs/api-reference.md) — every public/admin API,
  parameters, errors, and copyable examples;
- [`docs/azure-deployment.md`](docs/azure-deployment.md) — production topology,
  credentials, secrets, migrations, deployment, backup, and rollback;
- [`docs/final-acceptance.md`](docs/final-acceptance.md) — verification evidence,
  reviewer flow, failure states, and explicit external gates;
- [`docs/frontend-premium-redesign-plan.md`](docs/frontend-premium-redesign-plan.md)
  — implemented visual direction, GSAP motion plan, phased LOC, and acceptance
  record;
- [`docs/PROJECT-EXPLAINER.md`](docs/PROJECT-EXPLAINER.md) — plain-language
  explanation of the problem, architecture, features, data flow, APIx,
  sources, local demo, limitations, and judge questions;
- [`docs/master-phase-status.md`](docs/master-phase-status.md) — canonical status
  for Phases 0–16.

## Prerequisites

- Python 3.12 or newer;
- Node.js 22 or newer;
- PostgreSQL 16 or newer, or Docker Compose.

## Local setup

From the project root:

```bash
cp .env.example .env
make install
```

Set `DATABASE_URL` in `.env` to your PostgreSQL database, then run:

```bash
set -a
. ./.env
set +a
make migrate
make seed
```

Start the backend from the project root:

```bash
.venv/bin/uvicorn --app-dir backend app.main:app --reload --port 8000
```

In a second terminal, start React:

```bash
npm --prefix frontend run dev
```

Open:

- React: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/health`
- Database readiness: `http://localhost:8000/ready`

## Run the Phase 3 fixture pipeline

With the database migrated:

```bash
set -a
. ./.env
set +a
make demo
```

This creates one `SYNTHETIC` run for the current Asia/Kolkata date. It plans 15
jobs (3 routes × 5 windows), stores deterministic raw quotes, and creates
normalized observations. Repeating it returns the existing run rather than
duplicating data.

## Calculate the Phase 8 prototype APIx

After a completed or partial collection run, calculate its persisted index:

```bash
make apix RUN_ID=replace-with-collection-run-uuid
```

The command creates the 15-item versioned basket when needed, stores each
route-window median and its canonical-fare input links, freezes the base after
seven eligible dates, and stores the exact component calculation. Before the
base is ready, the result is intentionally `PROVISIONAL_BASE` with no published
index value. Repeating the command for the same run is idempotent.

The protected API equivalent is:

```bash
curl -X POST http://localhost:8000/api/v1/admin/collection-runs/fixture \
  -H 'X-Admin-Token: change-me-before-use'
```

Never use the example token outside local development.

Phase 13 period aggregates refresh automatically whenever a daily index is
calculated. To backfill weekly and monthly rows for existing daily indices:

```bash
curl -X POST 'http://localhost:8000/api/v1/admin/index/aggregate?data_class=SYNTHETIC' \
  -H 'X-Admin-Token: change-me-before-use'
```

Read the evidence at `/api/v1/index/current/coverage`,
`/api/v1/index/weekly`, and `/api/v1/index/monthly`.

## Run the Phase 14 historical back-test

The bundled reference file contains four air-fare item-index values transcribed
from Annexure V of MoSPI's October 2025 CPI release. Import it into the separate
historical tables:

```bash
set -a
. ./.env
set +a
make historical \
  CSV=data/reference/mospi-airfare-cpi-sample.csv \
  CODE=MOSPI-AIRFARE-CPI-2012-2025-10-SAMPLE \
  TITLE="MoSPI All India CPI air fare item sample" \
  PUBLISHER="Ministry of Statistics and Programme Implementation" \
  SOURCE_URL="https://cpi.mospi.gov.in/PDFile/Press/PR%20October%202025.pdf" \
  LICENSE="Government Open Data License - India" \
  METRIC="Air fare economy class adult All India Combined CPI"
```

On a clean demonstration database, `make backtest` creates exactly 30 days of
labelled synthetic collection/index evidence and prints the overlap and
correlation status. It never converts that evidence into `LIVE` data.

Read the report at:

```text
/api/v1/historical/backtest?dataset_code=MOSPI-AIRFARE-CPI-2012-2025-10-SAMPLE&data_class=SYNTHETIC
```

## Phase 15 exports

The following endpoints keep the requested data class explicit:

```text
/api/v1/exports/fare-observations.csv?data_class=SYNTHETIC
/api/v1/exports/index.csv?data_class=SYNTHETIC
/api/v1/exports/period-index.csv?data_class=SYNTHETIC
/api/v1/exports/backtest.csv?dataset_code=...&data_class=SYNTHETIC
/api/v1/exports/package.json?dataset_code=...&data_class=SYNTHETIC
/api/v1/exports/analysis.xlsx?dataset_code=...&data_class=SYNTHETIC
```

The JSON and Excel packages include generation time, methodology and missing-
data versions, coverage, statuses, reference provenance, and raw/normalized
lineage identifiers.

## Configure the first documented real-source adapter

Phase 4 uses Duffel's documented Flights API. It does not scrape an airline or
OTA website. Read `docs/source-reviews/duffel.md` and the current provider
agreement before enabling it.

Create a backend-only token in your Duffel account and place it in `.env`:

```bash
DUFFEL_ACCESS_TOKEN=replace-with-your-backend-only-token
DUFFEL_SOURCE_APPROVED=true
DUFFEL_SOURCE_ENABLED=true
```

For a Duffel test token, keep:

```bash
DUFFEL_LIVE_MODE=false
```

The resulting rows are stored as `RECORDED_DEMO`, because Duffel says its test
mode does not provide realistic schedules or prices. Never present them as
live. Run the configured test-mode source with:

```bash
set -a
. ./.env
set +a
make duffel
```

For an activated production account and live token only, set
`DUFFEL_LIVE_MODE=true`. The adapter also requires the returned API payload to
declare `live_mode=true`; a mismatch fails closed.

The protected API equivalent is:

```bash
curl -X POST http://localhost:8000/api/v1/admin/collection-runs/duffel \
  -H 'X-Admin-Token: replace-with-your-admin-token'
```

To schedule Duffel instead of the fixture after it is configured:

```bash
SCHEDULER_ENABLED=true
SCHEDULED_SOURCE=duffel
```

## Configure an explicitly permissioned web source

This is the project's own small scraping/extraction engine. It does not bypass
CAPTCHAs or source restrictions, and no airline is approved by default. First
read `docs/source-reviews/web-collection-candidates.md`. Obtain written
permission, copy
`backend/config/source-profiles/permissioned-web.example.json`, and replace its
URL/selectors with the approved source contract. Then configure:

```bash
WEB_SOURCE_PROFILE_PATH=config/source-profiles/your-approved-source.json
WEB_SOURCE_ENABLED=true
WEB_SOURCE_APPROVED=true
WEB_SOURCE_PERMISSION_REFERENCE=your-saved-letter-or-contract-reference
SCHEDULED_SOURCE=permissioned_web
```

Install Chromium once for a non-Docker setup and run the source:

```bash
.venv/bin/playwright install chromium
make web
```

Docker installs Chromium during the backend image build. If permission or a
profile is absent, the command refuses before opening a browser. A robots
denial, CAPTCHA, block, timeout, or changed page structure is stored as its
exact failure rather than bypassed or silently repaired.

Collection uses one scheduler-independent worker boundary, a finite adapter
timeout, at most two transient retries, bounded backoff, source rate limiting,
structured terminal failures, and per-day idempotency.

## Verification

```bash
make lint
make typecheck
make test
make build
```

To verify migrations against a disposable SQLite database without affecting
your configured database:

```bash
DATABASE_URL=sqlite+pysqlite:////tmp/airfare-apix-migration-check.db \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
DATABASE_URL=sqlite+pysqlite:////tmp/airfare-apix-migration-check.db \
  .venv/bin/alembic -c backend/alembic.ini downgrade base
DATABASE_URL=sqlite+pysqlite:////tmp/airfare-apix-migration-check.db \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
```

## Docker Compose

```bash
cp .env.example .env
# Replace the placeholder POSTGRES_PASSWORD and ADMIN_TOKEN in .env.
docker compose up -d --build
```

After the PostgreSQL health check passes, the backend migrates the database and
starts. React is available on port 5173.

Check all services and open the application:

```bash
docker compose ps
curl http://localhost:8000/ready
```

- Application: `http://localhost:5173`
- API documentation: `http://localhost:8000/docs`
- Source health: `http://localhost:8000/api/v1/sources/health`

The local PostgreSQL instance is free and needs no Azure account or paid
subscription. Its data is kept in the named `postgres_data` Docker volume.

For the PostgreSQL integration test, create and migrate a separate test
database once:

```bash
set -a
. ./.env
set +a
docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" airfare_apix_test'
DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_HOST_PORT:-5432}/airfare_apix_test" \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
TEST_DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_HOST_PORT:-5432}/airfare_apix_test" \
  .venv/bin/pytest -q backend/tests/test_postgresql_integration.py
```

If that database already exists, skip only the `createdb` line.

Shutdown without deleting PostgreSQL data:

```bash
docker compose down
```

Delete the development database volume only when you explicitly want a clean
database:

```bash
docker compose down --volumes
```

## Troubleshooting

- **`/ready` says unavailable:** check `DATABASE_URL`, confirm PostgreSQL is
  running, then run `make migrate`.
- **React reports backend unavailable:** confirm FastAPI is on port 8000 and
  `VITE_API_BASE_URL=http://localhost:8000`.
- **A migration fails on an old local database:** do not delete data blindly;
  inspect `alembic current` and `alembic history` first.
- **The fixture command returns an existing run:** this is the intended
  idempotency protection. Use a different methodological date in the CLI only
  when you deliberately need another synthetic run.
- **Docker is unavailable:** use the local setup with a separately installed
  PostgreSQL server.
- **Docker says permission denied:** sign out and back in once after adding
  your account to the `docker` group, then retry `docker compose ps`.

## Methodological warning

Synthetic or recorded-demo data must never be presented as live airfare data.
The implementation calculates a prototype APIx and historical comparison, not
an official national statistic. See `docs/methodology.md` for the frozen
formula, validation method, and limitations.
