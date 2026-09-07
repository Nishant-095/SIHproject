# SIH26056 Airfare APIx — MVP Architecture Contract

**Status:** Phase 0 frozen  
**Version:** 0.2.0  
**Effective date:** 2026-09-05

## 1. Purpose

The product is a small, auditable statistical data system for Indian domestic
airfares. It collects comparable fare quotes on a controlled schedule, keeps
the raw evidence, derives quality-controlled observations, calculates a
prototype Airfare Price Index (APIx), and exposes the results through an API
and a React dashboard.

Its primary question is:

> Where did this APIx value come from?

The system must answer that question down to the source-specific raw quote,
collection job, query, flight, travel date, collection timestamp, parser
version, normalization decision, and inclusion decision.

## 2. MVP boundary

The Level-A MVP includes:

- three routes: `DEL-BOM`, `DEL-BLR`, and `BOM-BLR`;
- five advance windows: `T1`, `T7`, `T15`, `T30`, and `T45`;
- one scheduled collection at 10:00 Asia/Kolkata each day;
- one fixture adapter and at least one reviewed, permitted real adapter;
- raw and normalized storage;
- deterministic flight identity and duplicate handling;
- essential quality checks;
- a transparent, fixed-weight prototype APIx;
- FastAPI endpoints;
- a four-page React dashboard;
- automated tests for critical calculations and the main data path.

The MVP does not include booking, predictions, recommendations, consumer
accounts, alerts, mobile applications, Kubernetes, Hadoop, Spark, blockchain,
LLM features, or continuous high-frequency scraping.

## 3. Lean system topology

```text
React + Vite dashboard
          |
          | HTTP / JSON
          v
FastAPI application ----------------------------------+
  |                                                   |
  +-- API routes                                      |
  +-- collection planner                              |
  +-- APScheduler daily trigger                       |
  +-- source-adapter registry                         |
  +-- normalization and QA                            |
  +-- canonical-fare service                          |
  +-- APIx service                                    |
          |                                           |
          v                                           |
     PostgreSQL                                       |
          ^                                           |
          |                                           |
Fixture adapter + approved real adapter(s) -----------+
```

The MVP is a modular monolith: one backend codebase and one database. Internal
modules have explicit responsibilities, but they are not separate services.

Development containers are limited to:

```text
postgres
backend
frontend
```

Redis, Celery, object storage, and separate worker services are deferred until
measured collection volume or reliability needs justify them.

## 4. Technology decisions

| Concern | MVP decision | Reason |
|---|---|---|
| Frontend | React + Vite + TypeScript | A client-rendered dashboard does not require server rendering. |
| Routing | React Router | Four clear application pages. |
| Charts | Lightweight semantic React SVG | Current data volume needs no chart library; visible labels and fallback tables preserve auditability. |
| Backend | FastAPI on Python 3.12+ | Typed APIs and suitable statistical tooling. |
| Database | PostgreSQL | Relational integrity, decimal money, indexing, and audit queries. |
| ORM | SQLAlchemy 2.x | Explicit relational persistence. |
| Migrations | Alembic | Repeatable schema evolution. |
| Scheduling | APScheduler | Adequate for one controlled daily MVP run. |
| Backend tests | pytest | Unit, API, and integration testing. |
| Frontend tests | Vitest | Focused component and utility tests. |
| Browser verification | In-app Chromium/Playwright workflow | Critical routes and responsive views are smoke-tested against the live local stack. |

## 5. End-to-end data flow

```text
Basket and source configuration
  -> collection planner
  -> one collection run
  -> route x window x source jobs
  -> source adapter response
  -> immutable raw quote
  -> normalized fare observation
  -> quality flags and eligibility
  -> physical-flight identity
  -> canonical physical-flight fare
  -> daily route-window price
  -> price relative against the base period
  -> fixed-weight APIx and coverage
  -> weekly/monthly APIx with daily-index lineage and confidence metadata
  -> FastAPI
  -> React dashboard and exports
```

No dashboard component calculates APIx. No source adapter performs
normalization, cross-source deduplication, weighting, or aggregation.

## 6. Module responsibilities

The backend will use a compact structure:

```text
backend/app/
  main.py
  config.py
  db/
  models/
  schemas/
  collectors/
    base.py
    registry.py
    fixture.py
    providers/
  pipeline/
    normalize.py
    quality.py
    canonicalize.py
  indexing/
    methodology.py
    service.py
  services/
    collection.py
    planner.py
    provenance.py
  api/
  scheduler.py
```

- **Collectors** query one source and return source-shaped raw quotes plus
  structured failures.
- **Collection services** create runs/jobs, invoke collectors, and persist raw
  results.
- **Pipeline** converts raw values into normalized observations and records
  deterministic QA decisions.
- **Canonicalization** prevents one physical flight receiving extra weight only
  because it appears through several sources.
- **Indexing** consumes eligible canonical fares and a versioned basket. It has
  no source-specific logic.
- **API** reads persisted results and provenance through services. It does not
  contain statistical calculations.
- **React** presents API responses. It never connects directly to PostgreSQL.

## 7. Provenance chain

Every published daily index retains this chain:

```text
daily_index
  -> daily_index_component
  -> daily_route_window_price
  -> canonical_fare
  -> fare_observation
  -> raw_quote
  -> collection_job
  -> collection_run
  -> source
```

Required version fields are retained alongside the chain:

- parser version on each raw quote;
- normalization version on each observation;
- canonicalization policy version on each canonical fare;
- basket and methodology versions on each index result.

Raw quotes are append-only in normal operation. A correction creates a new
derived result or processing version; it does not rewrite the captured source
evidence.

## 8. Data-class separation

Every run and resulting record is classified as one of:

- `LIVE`: obtained by the running system from an approved source;
- `HISTORICAL`: imported from an identified external reference dataset;
- `SYNTHETIC`: invented solely for tests and development;
- `RECORDED_DEMO`: permitted recorded source-shaped material used for a stable
  demonstration.

Synthetic and recorded-demo data never enter a live APIx series. The dashboard
must display the active classification prominently.

## 9. Runtime and failure behaviour

- APScheduler requests one daily run at 10:00 Asia/Kolkata.
- The planner creates one job per active route, advance window, and enabled
  source.
- Jobs have stable idempotency keys so a retry cannot create an accidental
  second observation for the same source query and scheduled run.
- One job or source failure does not fail unrelated jobs.
- A source failure is recorded as a source failure, never as `SOLD_OUT`.
- A blocked or restricted source is disabled without changing the planner,
  normalization, index engine, or frontend.
- The dashboard reads precomputed daily results rather than recomputing the
  index for each request.

## 10. Security and operational boundaries

- Secrets live in environment variables and are never committed.
- Administrative collection triggers use an environment-based MVP token.
- No CAPTCHA bypass, credential misuse, fingerprint evasion, proxy rotation,
  or anti-bot circumvention is permitted.
- Source rate limits are configuration, not hard-coded inside adapters.
- Raw payload retention is limited to permitted material necessary for
  reproducibility.
- Personally identifiable traveller data is neither required nor collected.

## 11. Architecture change rule

This contract is frozen for the MVP. A change requires a short decision record
containing the problem, evidence, chosen change, migration effect, and impact on
reproducibility. Complexity may be added only to solve an observed constraint.

## 12. Phase 4–8 implementation note

The first real-source integration is a documented Duffel Flights API adapter.
It is disabled and pending approval by default. Test-mode responses are stored
as `RECORDED_DEMO`; only an explicitly configured live token plus a response
declaring live mode can create `LIVE` rows.

A provider-neutral `PermissionedWebAdapter` implements the requested browser
extraction architecture without claiming that an airline has granted access.
A versioned JSON profile maps one approved same-origin search page to the
common adapter fields. Before Chromium opens a page, the adapter requires an
operator approval reference and a positive robots decision. It serializes
requests to honor crawl delay and records structured failures for restrictions,
CAPTCHA, timeouts, blocking, and parser changes. Only configured fare fields,
page metadata, robots evidence, and the permission reference enter raw storage;
HTML, screenshots, credentials, and traveller identity do not.

Collection remains a modular monolith. A scheduler-independent worker provides
finite timeouts, a maximum of three total attempts, bounded backoff,
source-specific pacing, failure isolation, and restart-safe attempt budgets.
This avoids introducing Redis or Celery for only 15 jobs per source per day.

Normalization validates route, carrier, travel date, booking window, data
class, source lineage, availability, cabin, currency, nonstop status, and fare
values. Eligible observations are linked to `canonical_fares` without deleting
their source evidence. Canonical selection uses the versioned
`direct-then-median-v1` rule: use the median of approved direct-airline source
representatives when present, otherwise the median of approved source
representatives. Minimum, maximum, dispersion, counts, conflict status, and
each observation's role are retained.

Phase 8 implements the index as a small isolated `indexing` module. The basket,
weights, frozen base prices, and their input identifiers are database rows, not
collector or UI constants. Each completed/partial run produces 15 deterministic
route-window median rows; relational input links retain every canonical fare
used. Decimal price relatives and renormalized fixed weights are then persisted
as 15 index components plus one daily result with coverage, publication status,
methodology version, canonicalization version, and exact run ownership. No API
route or dashboard component performs statistical calculation.

Phase 13 keeps the same modular-monolith boundary. Recalculating a daily index
refreshes its calendar week and month in `period_indices`, while
`period_index_inputs` preserves every daily row considered. Coverage APIs join
existing index components and provenance to report source dispersion and
route-level missing windows. The React dashboard only presents these persisted
or server-derived facts; it does not aggregate the series itself.

Phases 14 and 15 add two small modules without changing collection. Historical
reference rows enter only through a strict import service and live in separate
`historical_datasets` and `historical_index_observations` tables. Dataset codes
are immutable: changed content requires a new versioned code, while the same
content is idempotent. Monthly comparisons rebase the internal and reference
series at their first common month; correlation is emitted only with enough
non-constant overlap. Route comparisons are derived from retained daily index
components, so they preserve the same basket weights and coverage evidence.

Exports are read-only views over those persisted layers. CSV endpoints serve
focused tables, JSON serves a complete machine-readable package, and Excel
renders the same package into six review-friendly sheets. Every package states
its generation time, selected data class, methodology version, missing-data
policy, and available provenance; export code performs no index calculation.

## 13. Phase 1 entry gate

Phase 1 may begin when the methodology, source policy, data dictionary, and
Phase 0 checklist agree with this document. Phase 1 must implement the lean
React/FastAPI/PostgreSQL foundation without adding deferred infrastructure.
