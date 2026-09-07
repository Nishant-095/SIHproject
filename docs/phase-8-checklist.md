# Phase 8 — APIx Engine Completion Checklist

Verified on 2026-09-05 against the frozen methodology contract.

## Implementation

- ✅ Isolated basket, base, relative, weight, aggregation, methodology, and
  orchestration modules
- ✅ Versioned 15-item basket with database-backed equal weights
- ✅ Median daily canonical fare per route-window
- ✅ Relational canonical-fare input lineage
- ✅ Seven eligible-date base freeze with retained input identifiers
- ✅ Seeded demonstration base cannot replace a naturally frozen base
- ✅ Decimal price relatives and fixed-weight aggregation
- ✅ 80% publication threshold and exact coverage
- ✅ Missing components retained without fare imputation
- ✅ Daily result and all 15 component rows persisted
- ✅ Basket, methodology, aggregation, and canonicalization versions retained
- ✅ One official result owner per date/class/version
- ✅ Calculation accepts only completed or partial collection runs
- ✅ Repeated calculation is idempotent
- ✅ CLI command: `make apix RUN_ID=<uuid>`

## Verification

- ✅ Hand-calculated 102.00000000 fixture equals the code result
- ✅ Input order does not alter the result
- ✅ 80% coverage fixture publishes with correct weight renormalization
- ✅ Below-80% fixture is stored as insufficient coverage
- ✅ First six base-building dates remain provisional; date seven freezes base
- ✅ Naturally frozen base rejects seeded replacement
- ✅ SQLite migration round-trip and schema checks pass
- ✅ Main and isolated-test PostgreSQL migrations reach Phase 8 head
- ✅ PostgreSQL schema has no ungenerated model operations
- ✅ PostgreSQL calculation and component persistence tests pass
- ✅ Real local CLI creates once and returns the same result on repetition

## Boundary

- 🟡 Synthetic APIx is fully operational and verified.
- 🟡 A genuine `LIVE` APIx remains externally blocked until Phase 4 receives an
  activated approved API credential or written permission for a web source.
- ✅ Phase 9 index APIs and Phase 10 dashboard are implemented as separate layers.
