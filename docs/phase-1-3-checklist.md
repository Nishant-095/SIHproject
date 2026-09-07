# Phase 1–3 Implementation and Verification Checklist

**Created before implementation:** 2026-09-05  
**Rule:** An item is checked only after direct evidence proves it.

Status legend:

- `[ ]` Not yet verified
- `[x]` Implemented and verified
- `[!]` Implemented/configured but blocked from runtime verification by the local environment

## Phase 1 — Repository and foundation

### Structure and configuration

- [x] Lean monorepo structure exists for `backend`, `frontend`, `scripts`, `docs`, and CI.
- [x] `.env.example` documents backend, PostgreSQL, scheduler, admin token, CORS, and frontend API settings without containing a real secret.
- [x] `.gitignore` excludes secrets, virtual environments, dependencies, caches, databases, coverage, and generated build output.
- [x] Docker Compose defines only PostgreSQL, backend, and React frontend services with health/dependency behaviour.
- [x] README gives exact local and Docker startup, migration, test, shutdown, and troubleshooting instructions.

### Backend foundation

- [x] Python project metadata and pinned-compatible dependency ranges exist.
- [x] FastAPI application starts through an application factory/lifespan.
- [x] `/health` reports application liveness.
- [x] `/ready` checks database connectivity instead of claiming readiness blindly.
- [x] Environment configuration is typed and has safe development defaults.
- [x] Structured logging is configured without production `print()` calls.
- [x] SQLAlchemy session management supports PostgreSQL and isolated SQLite tests.
- [x] Alembic is configured from the same database URL contract.

### React foundation

- [x] Frontend is React + Vite + TypeScript and contains no Next.js dependency or configuration.
- [x] The application shell uses semantic navigation and route-aware document titles.
- [x] Backend status has stable loading, ready, and failure states with a retry action.
- [x] The shell is responsive, keyboard accessible, reduced-motion aware, and has a global visible scrollbar theme.
- [x] `DESIGN.md` records the product-specific visual direction and maps to runtime CSS tokens.
- [x] `UX-CONTRACT.md` records only the current shell/API behaviour and authoritative Phase 0 sources.

### Foundation gate

- [x] Backend imports and starts in the verification environment.
- [x] Frontend typecheck and production build pass.
- [x] Initial backend and frontend tests pass.
- [x] Alembic can create the Phase 1–2 schema in an isolated database.

## Phase 2 — Domain, database, normalization, and provenance

### Domain contract

- [x] Source, review, data-class, window, run, job, availability, quality, and failure enums are implemented.
- [x] Currency values use `Decimal`/`NUMERIC`, never binary floating point.
- [x] Observation timestamps are UTC-aware and methodological dates remain explicit.
- [x] Flight identity is reproducible from its canonical input string and SHA-256 hash.

### Persistence

- [x] `sources` model has review, enablement, rate, and parser-version fields.
- [x] `routes` model enforces a unique directed airport pair and different origin/destination.
- [x] `collection_runs` separates methodological date, scheduled time, actual times, trigger, status, counters, and data class.
- [x] `collection_jobs` has a unique idempotency key, structured failure, attempts, route, source, date, and window.
- [x] `raw_quotes` preserve source-shaped evidence, parser version, and content hash.
- [x] `fare_observations` link one-to-one to raw evidence and retain normalized values, quality decision, processing version, and exclusion reason.
- [x] Foreign keys and high-value uniqueness/check constraints are present in models and migration.
- [x] The initial Alembic migration matches the implemented Phase 2 model scope.

### Seed, normalization, and API path

- [x] Seed logic creates exactly the three frozen routes and one non-live fixture source idempotently.
- [x] Normalization converts an eligible fixture raw quote to one stored normalized observation.
- [x] Normalization excludes invalid currency, unsupported cabin/connection, missing fare, or incomplete identity with explicit reasons.
- [x] `GET /api/v1/routes` returns the frozen route configuration.
- [x] `GET /api/v1/observations/{id}` returns normalized data.
- [x] `GET /api/v1/observations/{id}/provenance` returns the raw-to-normalized decision chain.

### Phase 2 gate

- [x] One raw quote can become a stored normalized observation without a real scraper.
- [x] The stored observation can be retrieved together with exact raw provenance.
- [x] Targeted model, normalization, route, observation, and migration tests pass.

## Phase 3 — Fixture adapter, planner, collection, and scheduler

### Adapter and planner

- [x] A common asynchronous adapter interface accepts the frozen search request contract.
- [x] `FixtureAdapter` returns deterministic, realistic raw fare quotes without claiming live data.
- [x] Adapter registry resolves enabled fixture sources without scheduler/source-specific coupling.
- [x] Planner derives exact `T1`, `T7`, `T15`, `T30`, and `T45` travel dates from the methodological date.
- [x] Planner creates exactly 15 jobs for 3 routes × 5 windows × 1 fixture source.
- [x] Replanning the same run cannot create duplicate jobs.

### Collection and operation

- [x] Collection service creates a run, persists jobs, invokes the adapter, stores raw quotes, normalizes observations, and updates counters.
- [x] One job failure is recorded and does not abort unrelated jobs.
- [x] Raw quote content hashes are deterministic and duplicate raw payloads are not double-stored for one job.
- [x] APScheduler can request the daily 10:00 Asia/Kolkata run and remains disabled during tests by configuration.
- [x] Protected admin endpoint runs the fixture pipeline using an environment token.
- [x] Collection-run detail endpoint exposes planned/successful/failed job and observation counts.

### Phase 3 gate

- [x] One command/API request produces a persisted synthetic run with 15 successful jobs.
- [x] The run produces deterministic raw quotes and normalized observations for all route-window combinations.
- [x] Repeating the same methodological run is safely rejected or returns the existing run without data duplication.
- [x] Planner, adapter, collection, failure-isolation, API, and scheduler tests pass.

## Cross-phase quality audit

- [x] Backend formatter/linter passes.
- [x] Backend typecheck passes.
- [x] Complete targeted backend test suite passes.
- [x] Alembic upgrade → downgrade → upgrade passes on an isolated verification database.
- [x] PostgreSQL-specific models and Docker Compose configuration receive static validation.
- [x] Frontend lint passes.
- [x] Frontend tests pass.
- [x] Frontend typecheck passes.
- [x] Frontend production build passes.
- [x] `DESIGN.md` lint passes and documented tokens match runtime CSS values.
- [x] Premium UI strict audit passes.
- [x] UI anti-pattern search has no actionable native-dialog, non-semantic click, false-link, stale-request, hidden-scrollbar, or Next.js findings.
- [x] Live browser smoke test verifies loading/ready or failure/retry, keyboard navigation, narrow viewport, and honest non-live project status.
- [x] No Phase 4 real-source capability, live fare, APIx calculation, or completed dashboard is falsely claimed.

## Completion evidence

**Decision:** Phases 1, 2, and 3 are implemented and verified for the approved
synthetic-only scope.

- [x] `make lint` — Ruff and ESLint passed with zero errors or warnings.
- [x] `make typecheck` — mypy passed across 43 backend source files; TypeScript passed.
- [x] `make test` — 20 backend tests and 3 frontend tests passed.
- [x] `make build` — the React/Vite production build completed successfully.
- [x] Fresh SQLite migration verification — upgrade, Alembic drift check, downgrade, and re-upgrade passed.
- [x] PostgreSQL offline migration compilation produced 211 lines of valid dialect-specific DDL.
- [x] Docker Compose static validation confirmed exactly `postgres`, `backend`, and `frontend`, including the PostgreSQL health dependency chain.
- [x] Live API smoke — `/health` and `/ready` passed; the fixture request created one `COMPLETED` `SYNTHETIC` run with 15/15 successful jobs, zero failures, and 30 valid observations.
- [x] Live idempotency/provenance smoke — a repeated methodological run returned the same run with `created=false`; raw provenance returned a 64-character SHA-256 content hash.
- [x] Live browser smoke — unavailable and ready states, retry recovery, System/Contract navigation, route-title/focus management, 390×844 responsive layout without horizontal overflow, and zero console warnings/errors were verified.
- [x] `designmd lint DESIGN.md` — zero errors, zero warnings.
- [x] premium strict UI audit — zero findings.
- [x] Docker Engine 29.1.3 and Compose 2.40.3 are installed; the PostgreSQL 17.11, backend, and frontend containers start successfully and report healthy/running state.
- [x] PostgreSQL migrations run upgrade → drift check → downgrade → re-upgrade against a dedicated PostgreSQL database.
- [x] Main PostgreSQL data remains present after restarting both database and backend containers.

The two backend test warnings are upstream deprecation notices from FastAPI/Starlette test dependencies; they do not represent failed application checks.
