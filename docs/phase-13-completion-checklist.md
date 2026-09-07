# Phase 13 — Stronger Aggregation Completion Checklist

Completed: 2026-09-06

## Statistical engine

- [x] Calendar weeks use Monday–Sunday and months use their real calendar bounds.
- [x] Weekly and monthly APIx use only published daily values.
- [x] Missing, provisional-base, and insufficient-coverage values are not imputed.
- [x] Expected, observed, valued, and low-coverage day counts are persisted.
- [x] Average and minimum coverage are persisted.
- [x] Source count, aggregation status, confidence, and warnings are persisted.
- [x] A no-data period stores `null`, never a fabricated zero.
- [x] Every period aggregate retains relational links to its daily inputs.

## Coverage evidence

- [x] Current-index API reports source dispersion and percentage share.
- [x] Every route reports available/total windows, weighted coverage, source
  count, observation count, confidence, and exact missing windows.
- [x] The missing-data response names the 80% threshold, no-imputation rule,
  available-weight renormalization, and published-days-only period rule.
- [x] Single-source, missing-cell, poor-coverage, and non-published conditions
  generate explicit warnings.

## API and dashboard

- [x] `GET /api/v1/index/current/coverage` exposes coverage evidence.
- [x] `GET /api/v1/index/weekly` exposes persisted weekly aggregates.
- [x] `GET /api/v1/index/monthly` exposes persisted monthly aggregates.
- [x] Protected `POST /api/v1/admin/index/aggregate` backfills existing rows.
- [x] The React Overview shows confidence, warnings, source dispersion, route
  coverage, missing windows, and weekly/monthly status.
- [x] Poor coverage is visibly labelled and is never presented as complete.

## Verification gate

- [x] Unit tests cover full, partial, low-coverage, single-source, leap-month,
  and no-data periods.
- [x] API tests cover public metadata and protected aggregation.
- [x] PostgreSQL migration reaches `20260906_0006 (head)` in main and test DBs.
- [x] PostgreSQL integration verifies period rows and daily-input lineage.
- [x] Frontend tests and production build pass.
- [x] Whole backend suite passes: 101 tests, including 3 PostgreSQL integration
  checks; frontend suite passes: 5 tests; production build succeeds.
- [x] Browser smoke verifies the real PostgreSQL-backed Overview at desktop and
  375 px: Phase 13 sections render, no page-level horizontal overflow occurs,
  wide tables scroll locally, and no console warning/error is emitted.

The genuine `LIVE` source remains the separate Phase 4 external
credential/permission gate. Phase 13 is complete for the implemented pipeline
and does not claim a live multi-source series.
