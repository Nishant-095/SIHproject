# Pre-Phase-8 Completion Audit

**Audit date:** 2026-09-05  
**Authority:** canonical SIH26056 implementation specification plus current code,
tests, migrated PostgreSQL schema, and running Docker services.

This audit separates implemented software from external evidence. A passing
test is accepted only for the behavior it directly exercises.

## Requirement matrix

| Phase | Required outcome | Direct evidence | Status |
|---|---|---|---|
| 0 | Methodology, architecture, source policy, routes, windows and comparable fare contract are frozen | `methodology.md`, `architecture.md`, `source-policy.md`, `data-dictionary.md`, `phase-0-checklist.md` | ✅ Proven |
| 1 | FastAPI, React/Vite, PostgreSQL, Alembic, Docker, CI, settings and structured logging operate | `/health`, `/ready`, Compose health checks, migration round-trip, CI workflow, frontend build | ✅ Proven |
| 2 | Relational domain, raw and normalized layers, decimal money, lineage and seeded routes work | migrated models; stored manual-normalization test; observation and provenance API tests | ✅ Proven |
| 3 | Common adapter plus deterministic fixture completes request → raw → normalized → PostgreSQL | fixture pipeline and idempotency tests; persisted Docker database | ✅ Proven |
| 4 | Exactly one permissible real source produces genuine observations end to end | Duffel and permissioned-browser implementations exist, but no user-owned live token or written airline/OTA collection permission exists | 🟡 External evidence missing |
| 5 | Three routes × five windows × each requested source are planned idempotently | single-source 15-job and two-source 30-job planner tests | ✅ Proven |
| 6 | Daily scheduler, worker separation, retries, timeouts, failures, pacing and recovery operate | actual scheduler-callback test, retry/timeout/restart/failure-isolation tests, PostgreSQL repeated-date test | ✅ Proven |
| 7 | Every stored raw quote reaches deterministic normalized QA or an explainable rejection | normalization, malformed-input, duplicate, outlier, canonicalization, provenance and source-health tests | ✅ Proven |

## Real-source adapter evidence

The generic web collector now has direct tests for:

- permission refusal before browser access;
- same-origin profile, navigation and robots enforcement;
- `robots.txt` allow/deny, crawl delay and redirect handling;
- actual Chromium JavaScript rendering;
- normal results, explicit no-results, CAPTCHA and HTTP 503;
- compact raw evidence, normalization and canonical persistence in PostgreSQL;
- disabled-by-default configuration and source-health visibility.

Duffel has sanitized normal, empty, optional-field and malformed contract
fixtures and correctly labels test responses `RECORDED_DEMO`, not `LIVE`.

## Remaining gate

The only unmet pre-Phase-8 requirement is the Phase 4 sentence:
“system collects genuine source observations end-to-end.” Neither code nor a
local mock can prove that. It requires one of:

1. an activated, approved Duffel live token; or
2. written permission from one airline/OTA plus its approved extraction profile.

Until that external input exists, `PERMISSIONED_WEB` and Duffel remain disabled
and `PENDING_REVIEW`. Phase 8 must not turn fixture or contract data into a
claimed live index.
