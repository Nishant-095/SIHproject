# Phases 9–12 Completion Checklist

Verified on 2026-09-06 against the local Docker PostgreSQL runtime.

## Phase 9 — FastAPI Surface

- ✅ Current, history, and date-specific APIx endpoints
- ✅ Route detail, price history, source dispersion, and lead-time endpoints
- ✅ Filtered observation list, observation detail, and provenance endpoints
- ✅ Collection-run list and detail endpoints
- ✅ Source-health and quality-summary endpoints
- ✅ Fare-observation and index CSV exports
- ✅ Generic protected collection-run dispatch endpoint
- ✅ Protected index recalculation and source enable/disable endpoints
- ✅ Complete routes appear in generated OpenAPI

Gate: ✅ Every dashboard read uses a public HTTP API; no frontend database access.

## Phase 10 — Internal Dashboard

- ✅ Overview: current APIx, daily/weekly/monthly change, history, route matrix,
  coverage, classification, and update time
- ✅ Route explorer: route index, fare history, carriers, source dispersion,
  five-window context, and lead-time curve
- ✅ Provenance: source, collection identifiers, query, raw payload, normalized
  fare breakdown, quality status, flags, and inclusion decision
- ✅ Operations: latest run, jobs, failures, quality, source health, observation
  count, monitoring history, and coverage context
- ✅ Loading, empty, error, bounded timeout, and manual retry states
- ✅ Desktop and 375 px browser smoke tests with no page overflow
- ✅ Browser console has no errors or warnings across all four pages
- ✅ Synthetic/live data class remains visible

Gate: ✅ A reviewer can understand the full implemented system without database access.

## Phase 11 — Multi-source Adapter Contract

- ✅ Fixture adapter implements `FareSourceAdapter`
- ✅ Duffel adapter implements the same request/quote contract
- ✅ Permissioned-browser adapter implements the same contract
- ✅ Core collection, normalization, QA, and index code remains provider-neutral
- ✅ One test sends an identical request through all three adapter boundaries
- ✅ Permission, robots, mode, parser, rate-limit, timeout, and authentication
  failures remain structured and fail closed

Gate: ✅ The same request contract works across multiple providers. Production
credential or written-permission activation remains the separate Phase 4 external gate.

## Phase 12 — Source Health and Monitoring

- ✅ Last success and last structured failure
- ✅ Success/failure counts and success rate
- ✅ Average latency and parser version
- ✅ `HEALTHY`, `DEGRADED`, `BLOCKED`, `PARSER_CHANGED`, and `DISABLED`
- ✅ Historical daily success-rate endpoint and operations trend
- ✅ Persistent in-app warnings for degraded, blocked, and parser-change states

Gate: ✅ Operators can identify the failing source and failure class from the API
or dashboard without reading raw logs.

## Verification Evidence

- ✅ Backend Ruff: clean
- ✅ Backend mypy: 70 source files, no issues
- ✅ Backend pytest: 95 passed, including PostgreSQL integration tests
- ✅ Frontend ESLint: clean
- ✅ Frontend TypeScript: clean
- ✅ Frontend Vitest: 5 passed
- ✅ Frontend production build: successful
- ✅ Local services: PostgreSQL, FastAPI, and React running; database readiness connected
