# SIH26056 Master Phase Status

This tracker preserves the phase order and deliverables from the original
**Canonical Project Implementation Specification**. It maps them to the code
that is actually present and verified on 2026-09-06.

Status legend:

- ✅ Completed and verified
- 🟡 Partially implemented; the remaining work is stated explicitly
- ⬜ Not implemented yet
- 🔵 Environment/deployment task intentionally postponed to Azure

The original LOC figures are planning estimates, not targets. Generated files,
dependencies, build output, and raw data are excluded.

## Overall phase map

| Original phase | Original purpose | Original cumulative LOC | Current status |
|---|---|---:|---|
| 0 | Project contract | Not specified | ✅ Complete |
| 1 | Repository/foundation | 700–1,000 | ✅ Complete locally with Docker + PostgreSQL |
| 2 | Domain + database | 1,500–2,200 | ✅ Complete |
| 3 | Fake adapter | 2,000–2,700 | ✅ Complete |
| 4 | First real adapter | 2,800–3,700 | 🟡 Code/recorded path complete; production credential gate pending |
| 5 | Five-window job planner | 3,300–4,200 | ✅ Complete early |
| 6 | Scheduler/workers | 4,000–5,000 | ✅ Complete for MVP scope |
| 7 | Normalization + QA | 5,000–6,300 | ✅ Complete for MVP scope |
| 8 | APIx engine | 5,700–7,000 | ✅ Complete |
| 9 | FastAPI surface | 6,300–7,700 | ✅ Complete |
| 10 | Internal dashboard | 8,000–10,000 | ✅ Complete |
| 11 | Second/third source adapter | Not specified | ✅ Contract complete; production activation remains Phase 4 |
| 12 | Source health and monitoring | Not specified | ✅ Complete |
| 13 | Stronger aggregation | Not specified | ✅ Complete |
| 14 | Historical/back-test pipeline | Not specified | ✅ Complete |
| 15 | Export layer | Not specified | ✅ Complete |
| 16 | Documentation freeze | Not specified | ✅ Complete |

## Phase 0 — Project Contract

Original deliverables:

- ✅ `docs/methodology.md`
- ✅ `docs/architecture.md`
- ✅ `docs/source-policy.md`
- ✅ Supporting `docs/data-dictionary.md`
- ✅ Definition of one observation frozen
- ✅ Three MVP routes frozen: DEL→BOM, DEL→BLR, BOM→BLR
- ✅ Five windows frozen: T+1, T+7, T+15, T+30, T+45
- ✅ Allowed fare specification frozen
- ✅ Source strategy and compliance boundary frozen

Gate:

- ✅ The documents describe one consistent product and Phase 0 was formally closed.

## Phase 1 — Repository/Foundation

Original implementation tasks:

- ✅ Backend scaffold: FastAPI application factory and lifespan
- ✅ Frontend scaffold: React + Vite + TypeScript; no Next.js
- ✅ PostgreSQL-compatible configuration, models, constraints, and migration DDL
- ✅ Alembic migration framework
- ✅ Docker Compose with PostgreSQL, backend, and frontend services
- ✅ CI checks for backend, frontend, migration, and PostgreSQL service
- ✅ Typed environment settings
- ✅ Structured application logging
- ✅ Health and database-readiness endpoints
- ✅ README startup, migration, testing, shutdown, and troubleshooting instructions
- ✅ Local Docker Compose runtime uses PostgreSQL 17.11, FastAPI, and React

Gate:

- ✅ Backend starts
- ✅ Frontend starts
- ✅ Database migration runs completely in isolated SQLite verification
- ✅ PostgreSQL migration, drift check, downgrade, and re-upgrade pass against a dedicated database
- ✅ PostgreSQL data persists across database/backend container restarts
- 🔵 Execute the migration against the future Azure PostgreSQL instance
- ✅ Tests run

## Phase 2 — Domain + Database

Original implementation tasks:

- ✅ Domain enums
- ✅ SQLAlchemy models
- ✅ Pydantic schemas
- ✅ Initial migration
- ✅ Idempotent seed for exactly three routes
- ✅ Non-live fixture source seed
- ✅ Raw quote storage
- ✅ Normalized fare-observation storage
- ✅ Decimal/NUMERIC fare values
- ✅ UTC observation timestamps and explicit methodological dates
- ✅ Raw-to-normalized provenance relationship
- ✅ A stored observation was created through the fixture pipeline

Gate:

- ✅ A raw quote becomes a stored normalized observation without a scraper.

## Phase 3 — Fake Adapter

Original implementation tasks:

- ✅ Common asynchronous adapter contract
- ✅ Frozen fare-search request contract
- ✅ Deterministic `FixtureAdapter`
- ✅ Realistic but explicitly `SYNTHETIC` example fares
- ✅ Adapter registry
- ✅ Raw quote content hashing
- ✅ Raw quote persistence
- ✅ Normalized observation creation
- ✅ Fixture, adapter, collection, and failure tests

Gate:

- ✅ Search request → raw quote → database is verified end to end.

## Phase 4 — First Real Adapter

Original implementation tasks:

- ✅ Select one documented API source: Duffel Flights API
- 🟡 Record terms and manual review evidence; technical review is recorded, while operator acceptance/account approval remains external
- ✅ Keep the source disabled and `PENDING` until token, approval, and enablement are explicit
- ✅ Implement its adapter without changing the core pipeline
- ✅ Parse a normal response without fabricating missing fare components
- ✅ Handle no-flight results
- ✅ Handle malformed responses and test/live mode mismatch
- ✅ Handle authentication, rate limit, timeout, network, and source-unavailable failures
- ✅ Add sanitized normal, empty, missing-optional, and malformed fixtures plus tests
- ✅ Prove source-shaped contract fixtures through parser, raw storage, normalization, and canonicalization
- ✅ Implement a provider-neutral Playwright collector with declarative selectors, same-origin enforcement, permission gate, robots/crawl-delay compliance, CAPTCHA refusal, compact provenance, and structured failures
- ✅ Verify real JavaScript rendering locally and verify 15-job raw → normalized → canonical persistence in PostgreSQL
- 🟡 Bind that engine to a genuine airline/OTA: reviewed candidates do not permit this use without written permission
- 🟡 Collect genuine `LIVE` observations end to end: requires a user-owned activated live account/token

Gate:

- 🟡 The real adapter and contract-fixture path are verified; the genuine production-call gate cannot be truthfully closed without an activated user-owned credential.

## Phase 5 — Five-Window Job Planner

This original later phase was completed early while building the synthetic
pipeline.

Original implementation tasks:

- ✅ T+1 planning
- ✅ T+7 planning
- ✅ T+15 planning
- ✅ T+30 planning
- ✅ T+45 planning
- ✅ Planning for every configured route
- ✅ `collection_run` creation
- ✅ `collection_jobs` creation
- ✅ Exactly 15 jobs for 3 routes × 5 windows × 1 source
- ✅ Replanning cannot duplicate the run or its jobs

Gate:

- ✅ One command or API request produces the full daily collection plan.

## Phase 6 — Scheduler/Workers

Original implementation tasks:

- ✅ APScheduler daily trigger
- ✅ 10:00 Asia/Kolkata schedule
- ✅ Structured job failures
- ✅ Run and job idempotency
- ✅ One failed job does not abort unrelated jobs
- ✅ Scheduler can be disabled in tests and development
- ✅ Scheduler-independent reusable worker boundary
- ✅ Configurable finite adapter timeout
- ✅ At most two retries after the first attempt
- ✅ Exact transient-failure classification and bounded exponential backoff
- ✅ Source-specific rate limiting
- ✅ Structured terminal failure with final attempt count
- ✅ Explicit scheduled source and data-class selection
- ✅ Overlap prevention and daily idempotency
- ✅ Interrupted planned/running jobs resume within the original attempt budget
- ✅ Three simulated scheduled dates complete against PostgreSQL with 45/45 successful jobs
- 🟡 Several unattended genuine production days require the external Phase 4 live credential

Gate:

- ✅ Reliable scheduled/worker behavior is implemented and tested. Production-duration evidence is an operational Phase 4 dependency, not missing Phase 6 code.

## Phase 7 — Normalization + QA

Original implementation tasks:

- ✅ Airport aliases for the frozen DEL, BOM, and BLR basket with unknown/mismatch rejection
- ✅ Maintainable Indian carrier code/name alias dictionary
- ✅ Fare decomposition
- ✅ Flight identity input and SHA-256 identity
- ✅ True-duplicate protection inside a collection job
- ✅ Multi-source canonical fare and observation-link tables
- ✅ Configurable deterministic direct-airline-first or approved-source median policy
- ✅ Minimum, maximum, dispersion, source count, conflict, role, and method-version evidence
- ✅ Missing/invalid fare handling
- ✅ Non-negative fare, availability, route, travel-date, booking-window, source, and data-class checks
- ✅ Unsupported currency handling
- ✅ Unsupported cabin and connecting-flight handling
- ✅ Fare-component consistency flag
- ✅ Explicit quality flags, score, eligibility, and exclusion reason
- ✅ Ineligible and unapproved observations stay out of canonical/index-ready data
- ✅ Every stored observation has an explainable status and retained raw provenance
- ✅ Normalization exceptions retain their raw quote and create an excluded, explainable observation
- ✅ Deterministic MAD outlier flagging marks suspicious fares without deleting evidence
- ✅ Canonical representative policy is configurable and versioned
- ✅ Route/carrier indexes are present in the migrated PostgreSQL schema
- ✅ Source-health API exposes status, successes, failures, rate, latency, parser version, and last events

Gate:

- ✅ Normalization, cross-source canonicalization, duplicate handling, and provenance are implemented and verified for the frozen MVP specification.

## Phase 8 — APIx Engine

Original implementation tasks:

- ✅ Versioned 3-route × 5-window basket abstraction
- ✅ Positive configurable weights stored in database rows
- ✅ Seven-date base period with exact aggregate identifiers retained
- ✅ Seeded base restricted to non-production demonstration workflows
- ✅ Decimal price relatives (`100 × current / base`)
- ✅ Median canonical fare aggregation by route and window
- ✅ Missing-item coverage and available-weight renormalization
- ✅ Result, component, aggregate, and relational input persistence
- ✅ Methodology and upstream canonicalization versions stored
- ✅ Hand-calculated test datasets
- ✅ Exact deterministic and input-order-independent APIx tests
- ✅ Main and test PostgreSQL migrations plus schema-drift check
- ✅ PostgreSQL calculation/persistence integration test

Gate:

- ✅ The same dataset always produces the exact expected APIx.

## Phase 9 — FastAPI Surface

Original implementation tasks:

- ✅ FastAPI application and generated OpenAPI documentation
- ✅ Liveness and database-readiness endpoints
- ✅ Frozen-route endpoint
- ✅ Normalized-observation endpoint
- ✅ Raw-to-normalized provenance endpoint
- ✅ Collection-run detail endpoint
- ✅ Protected fixture-run administration endpoint
- ✅ Frontend uses HTTP APIs rather than PostgreSQL directly
- ✅ Latest APIx endpoint
- ✅ APIx time-series endpoint
- ✅ Route price-series endpoint
- ✅ Lead-time-curve endpoint
- ✅ QA-summary endpoint
- ✅ Source-health endpoint
- ✅ Export endpoints

Gate:

- ✅ The complete dashboard API surface is available through documented HTTP endpoints.

## Phase 10 — Internal Dashboard

Original implementation tasks:

- ✅ React application shell
- ✅ Responsive navigation and route-aware titles
- ✅ Honest loading, ready, failure, and retry states
- ✅ Honest synthetic/live boundary
- ✅ System-readiness page
- ✅ Frozen MVP-contract page
- ✅ Mobile-width and console-error browser verification
- ✅ APIx overview page
- ✅ Route explorer
- ✅ Observation/provenance page
- ✅ Collection operations page
- ✅ Lead-time price curve
- ✅ Coverage and quality visualizations

Gate:

- ✅ The judge can understand APIx, route trends, provenance, and operations solely through the dashboard.

## Internal Hackathon Freeze Point

Original freeze checklist mapped to the current implementation:

- ✅ 3 routes
- ✅ 5 windows
- 🟡 1 real source — adapter/recorded path complete; activated production credential pending
- ⬜ 2 real sources — preferred, not required for the first freeze
- ✅ Scheduler and finite worker reliability
- ✅ Raw storage
- ✅ Normalization for the frozen MVP routes, carriers, and fare contract
- ✅ Basic quality flags
- ✅ Same-source duplicates and multi-source canonical fare resolution
- ✅ Prototype APIx
- ✅ REST API — foundation, index, series, QA, monitoring, provenance, and export endpoints work
- ✅ Dashboard — all four required product pages work
- ✅ Lead-time curve
- ✅ Provenance — API chain and dedicated dashboard screen work
- ✅ Tests — backend, frontend, migration, and PostgreSQL integration suites pass

Do not delay the internal MVP for the original explicitly deferred items:

- machine learning
- mobile application
- user accounts
- fare forecasting
- Kubernetes
- ten source adapters
- complete India coverage

## Phase 11 — Second/Third Source Adapter

- ✅ Duffel adapter implements the shared contract with sanitized provider fixtures
- ✅ Permissioned-browser adapter implements the same contract with explicit permission and robots gates
- ✅ Core collection, normalization, and index pipeline stays unchanged
- ✅ One contract test sends the same request through fixture, Duffel, and permissioned-browser providers

Gate:

- ✅ The same search request works against multiple providers. Genuine production activation remains the separate Phase 4 external credential/permission gate.

## Phase 12 — Source Health & Monitoring

- ✅ Last successful collection timestamp
- ✅ Failure count and last structured failure
- ✅ Success rate
- ✅ Parser version visibility
- ✅ Average latency
- ✅ `HEALTHY` status
- ✅ `DEGRADED` status
- ✅ `BLOCKED` status
- ✅ `PARSER_CHANGED` status
- ✅ `DISABLED` status
- ✅ Historical source-success API and operations chart
- ✅ Persistent in-app alerts for `DEGRADED`, `BLOCKED`, and `PARSER_CHANGED`

## Phase 13 — Stronger Aggregation

- ✅ Source dispersion
- ✅ Route coverage
- ✅ Missing-data policies
- ✅ Confidence and coverage metadata
- ✅ Weekly aggregation
- ✅ Monthly aggregation
- ✅ Never hide poor coverage

Gate:

- ✅ Weekly and monthly values are persisted with daily-index lineage, and the
  API plus React overview expose partial periods, poor coverage, missing cells,
  source concentration, and confidence instead of silently filling gaps.

## Phase 14 — Historical / Back-Test Pipeline

- ✅ Create `scripts/import_historical.py`
- ✅ Store official/reference data separately with provenance
- ✅ Route-level comparison
- ✅ Monthly aggregation
- ✅ Deviation calculation
- ✅ Correlation where statistically meaningful, with explicit reasons when it is not
- ✅ Coverage calculation
- ✅ Accumulate or import enough evidence for a 30-day demonstration/back-test

Gate:

- ✅ A deterministic 30-day `SYNTHETIC` series is compared across two monthly
  periods with a separately imported, source-linked MoSPI reference sample.
  The engine exposes monthly deviations, route comparisons, coverage, and an
  honest `INSUFFICIENT_OVERLAP` result rather than fabricating a correlation.

## Phase 15 — Export Layer

- ✅ CSV export
- ✅ Excel export
- ✅ JSON export
- ✅ Include generation timestamp
- ✅ Include methodology version
- ✅ Include relevant coverage/provenance metadata

Gate:

- ✅ Daily, period, observation, historical, and back-test data can be exported
  without combining data classes. The six-sheet workbook and JSON package carry
  generation, methodology, coverage, status, and provenance fields.

## Phase 16 — Documentation Freeze

- ✅ README foundation
- ✅ Architecture
- ✅ Source policy
- ✅ Data dictionary
- ✅ Sampling methodology
- ✅ Installation and local operation instructions
- ✅ Current automated-testing commands
- ✅ Current limitations and synthetic-data boundary
- ✅ Final prototype APIx/index methodology
- ✅ Complete public API documentation and examples
- ✅ Real-adapter operating notes, review record, safe defaults, and recorded-mode instructions
- ✅ Production/Azure deployment guide
- ✅ Final end-to-end testing and acceptance document
- ✅ Product context and explicit evidence boundary
- ✅ Current-dashboard baseline screenshots
- ✅ Premium frontend redesign plan, phased LOC estimate, motion contract, and
  visual acceptance gates

Gate:

- ✅ Phase 16 documentation freeze is complete. Local synthetic-prototype
  acceptance is recorded without claiming either Azure deployment or a genuine
  Phase 4 production-source observation.

## Current verified implementation size

This is a snapshot, not a target:

- Backend application, migrations, and scripts: approximately 8,951 lines
- Backend tests and sanitized parser fixtures: approximately 3,704 lines
- React runtime and styles: approximately 1,912 lines
- Frontend tests: approximately 98 lines
- Frontend configuration/tooling excluding the generated lockfile: approximately 149 lines
- Phase/project documentation: approximately 3,615 lines

The implementation remains deliberately compact: the API, four-page analytical
dashboard, multi-adapter contract, and health monitoring use the same modular
pipeline without a separate queue system.

## Correct next implementation order

The requirement-by-requirement evidence is recorded in
`docs/pre-phase-8-completion-audit.md`.

1. 🟡 Close the final Phase 4 external gate with either an approved Duffel live token or written permission for one configured web source, then capture one genuine production observation.
2. ✅ Phase 8: implement and hand-verify the prototype APIx engine.
3. ✅ Phase 9: index, series, curve, QA, administration, and export APIs.
4. ✅ Phase 10: four required dashboard pages.
5. ✅ Re-run the internal hackathon freeze checklist.
6. ✅ Phases 11–12: cross-provider adapter contract and source monitoring.
7. ✅ Phase 13 stronger aggregation is complete against the verified synthetic
   pipeline; genuine LIVE aggregation remains dependent on the separate Phase 4
   production-source gate.
8. ✅ Phase 14 historical import/back-test and Phase 15 CSV/JSON/Excel exports
   are complete, including the 30-day labelled synthetic validation scenario.
9. ✅ Phase 16 API, Azure, product, and final-acceptance documentation is
   complete.
10. 🔵 Implement the separately approved premium frontend redesign plan; this
    is presentation work after the original 0–16 implementation roadmap.

Azure PostgreSQL and container deployment can safely be done later using
`docs/azure-deployment.md`. Local PostgreSQL runtime and migrations are
verified; hosted connectivity/readiness, managed secrets, and backup restore
remain unverified until Azure resources are actually provisioned.
