# Phase 14–15 Completion Checklist

Verified on 2026-09-06 against the canonical SIH26056 implementation plan.

## Phase 14 — Historical / Back-Test Pipeline

- ✅ `scripts/import_historical.py` imports provenance-aware CSV data.
- ✅ Imported reference data is stored only in `historical_datasets` and
  `historical_index_observations` with publisher, source URL, licence, metric,
  content hash, source record ID, status, import time, and raw record metadata.
- ✅ `LIVE`, `HISTORICAL`, `SYNTHETIC`, and `RECORDED_DEMO` remain separate.
- ✅ Monthly internal APIx is compared with national reference months after
  both series are rebased to 100 at their first common month.
- ✅ Every common month reports point and percentage deviation.
- ✅ Pearson correlation is calculated only for at least three non-constant
  overlapping months; otherwise an explicit reason is returned.
- ✅ Average internal coverage and each monthly coverage value are returned.
- ✅ Route-level monthly APIx, deviation from the overall APIx, observed days,
  expected days, and route coverage are returned.
- ✅ A deterministic 30-day synthetic run spans September–October 2025 and is
  compared with the separately stored MoSPI reference sample.
- ✅ Historical import, 30-day back-test, route comparison, APIs, and
  PostgreSQL persistence have automated tests.

Honesty boundary: the bundled MoSPI sample is a four-row, source-linked
reference extract, not a claim that MoSPI publishes route-level airfare prices.
The 30-day operational series is labelled `SYNTHETIC` and is never presented as
live data.

## Phase 15 — Export Layer

- ✅ Daily observations and APIx are available as CSV.
- ✅ Period APIx and the selected back-test are available as CSV.
- ✅ A complete machine-readable analysis package is available as JSON.
- ✅ A six-sheet Excel workbook is available with metadata, daily APIx,
  period APIx, observations, reference data, and back-test rows.
- ✅ Exports include generation timestamp and methodology version.
- ✅ Exports include data class, coverage, statuses, missing-data policy,
  parser/normalization versions, source IDs, raw quote IDs, hashes, reference
  publisher/source URL, and reference record IDs where relevant.
- ✅ Excel output has frozen headers, filters, readable widths, typed dates,
  and no hidden formulas or fabricated values.
- ✅ JSON, CSV, and Excel endpoints are covered by automated tests.

## Completion gate

- ✅ Phase 14 complete for the planned MVP scope.
- ✅ Phase 15 complete for the planned MVP scope.
- ✅ Genuine live validation remains the already-declared external Phase 4
  credential/permission dependency; it is not disguised as Phase 14 evidence.
