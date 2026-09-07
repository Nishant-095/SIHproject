# Airfare APIx: Complete Project Explainer

**Problem statement:** SIH26056, Real-Time Airfare Price Index for India  
**Project type:** auditable airfare statistics and data infrastructure  
**Current state:** complete local synthetic-data prototype; genuine live-source
operation and Azure deployment remain external gates

This guide explains the project without assuming prior knowledge of APIs,
databases, Docker, statistics, or frontend development.

## 1. The project in one minute

Air ticket prices change according to the route, airline, flight, travel date,
and how early the traveller searches. Looking at one fare does not explain how
the wider market is moving.

Airfare APIx creates a controlled measurement system. Every day it checks the
same route basket at the same time for five future travel windows. It keeps the
original source evidence, converts quotes into comparable observations, rejects
or flags unsuitable records, prevents the same physical flight from receiving
extra weight, and calculates a prototype index with base value 100.

The dashboard then answers two questions:

1. How are fares moving across the controlled basket?
2. Where did this exact index value come from?

The product does not book flights and does not predict future fares.

## 2. Original SIH objective

The canonical specification asks for an auditable platform that:

- collects comparable Indian airfare observations on a controlled schedule;
- preserves the raw evidence;
- normalizes and quality-checks observations;
- builds a configurable Airfare Price Index called APIx;
- exposes results through APIs and exports;
- presents the results through an interactive dashboard.

The governing rule is:

> Every final index value must be reproducible and traceable back to raw
> observations.

The word “real-time” means an operational collection system rather than a
manually prepared spreadsheet. The prototype uses one standardized daily
observation at 10:00 Asia/Kolkata. It does not scrape continuously every second.

## 3. What this application is and is not

### It is

- a small official-statistics style data platform;
- a scheduled fare-observation engine;
- a raw-to-index evidence pipeline;
- an API service for machine-readable access;
- an analytical dashboard;
- a reproducible prototype suitable for local SIH demonstration.

### It is not

- a MakeMyTrip or airline-booking clone;
- a ticket purchasing system;
- an AI prediction system;
- a personal fare-alert application;
- a manually maintained Excel dashboard;
- an official Government of India price index.

## 4. The controlled MVP basket

The current prototype deliberately stays small enough to understand and test.

### Routes

- Delhi to Mumbai: `DEL-BOM`
- Delhi to Bengaluru: `DEL-BLR`
- Mumbai to Bengaluru: `BOM-BLR`

### Advance booking windows

- `T+1`: travel tomorrow
- `T+7`: travel after seven days
- `T+15`: travel after fifteen days
- `T+30`: travel after thirty days
- `T+45`: travel after forty-five days

One source therefore produces 15 planned searches per daily run:

```text
3 routes × 5 booking windows × 1 source = 15 collection jobs
```

### Comparable fare definition

The sampling contract uses one adult, one-way travel, economy cabin, non-stop
flights where available, Indian rupees, and the same routes, windows, and
collection time. This avoids comparing unrelated products such as business
class against economy or connecting flights against non-stop flights.

## 5. Architecture in plain language

The application is a modular monolith. The backend remains one understandable
Python application, but each module has one responsibility.

```text
Route and source configuration
              |
              v
     Daily job planner
              |
              v
 Scheduler and reliable worker
              |
              v
 Source adapter: Fixture, Duffel, or approved web source
              |
              v
       Immutable raw quote
              |
              v
  Normalization and quality checks
              |
              v
 Canonical physical-flight fare
              |
              v
 Route-window price and APIx engine
              |
              v
          PostgreSQL
              |
              v
            FastAPI
       /                \
 React dashboard      CSV, JSON, Excel
```

Important separation rules:

- A collector only talks to one source and returns raw quotes.
- A collector never calculates APIx.
- The frontend never reads PostgreSQL directly.
- The frontend never calculates the index itself.
- FastAPI serves stored or server-derived results.
- PostgreSQL remains the system of record. CSV and Excel are exports.

## 6. What each technology does

| Technology | Meaning in this project |
|---|---|
| Python 3.12 | Runs collection, data processing, indexing, and backend logic. |
| FastAPI | Creates web endpoints that return JSON, CSV, and Excel. |
| PostgreSQL | Stores routes, jobs, raw quotes, observations, index results, and lineage. |
| SQLAlchemy | Lets Python read and write relational records safely. |
| Alembic | Applies versioned database schema changes. |
| APScheduler | Starts the selected collection source at the configured daily time. |
| httpx | Calls documented external APIs such as Duffel. |
| Playwright | Runs the permission-gated web extraction adapter for approved dynamic sites. |
| React + Vite + TypeScript | Builds the four-page analytical dashboard. |
| GSAP | Animates route traces and chart presentation only. |
| pytest and Vitest | Verify backend calculations and frontend behavior. |
| Docker Compose | Starts PostgreSQL, backend, and frontend together. |

Redis, Celery, Kubernetes, Hadoop, and Spark are intentionally absent. Fifteen
jobs per source per day do not justify that infrastructure in this prototype.

## 7. The complete data journey

Imagine a daily collection for `DEL-BOM` at `T+7`.

1. **Planning:** The planner creates one collection run and a job containing
   the route, travel date, booking window, source, and scheduled time.
2. **Collection:** The selected adapter returns fare quotes or a structured
   failure such as `NETWORK_TIMEOUT`, `NO_RESULTS`, or `PARSER_CHANGED`.
3. **Raw evidence:** The system stores source, request context, observed time,
   original fare fields, parser version, and content hash.
4. **Normalization:** Airport, carrier, flight, time, currency, cabin, and fare
   fields become one common schema. Money uses decimal arithmetic.
5. **Quality decision:** Each record receives flags and an inclusion decision.
   Source failure never becomes a zero fare or a sold-out flight.
6. **Flight identity:** Matching source quotes are grouped as one physical
   flight using carrier, number, route, date, and departure time.
7. **Canonical fare:** The engine selects one representative price and retains
   its source count, dispersion, range, and exact input links.
8. **Route-window price:** Eligible physical-flight fares produce a robust
   median for that basket cell.
9. **APIx:** The cell becomes a price relative against its frozen base price and
   contributes according to the configured weight.
10. **Presentation:** FastAPI exposes the persisted result. React displays it
    without recalculating it.

## 8. How the prototype APIx works

The prototype uses a fixed basket and a base value of 100.

```text
price relative = current route-window price / base route-window price

APIx = 100 × weighted average of available price relatives
```

Example:

```text
Base median fare     = ₹5,000
Current median fare  = ₹5,500
Price relative       = 5,500 / 5,000 = 1.10
Index contribution   = 110 before basket weighting
```

An APIx of 110 means the controlled basket is 10 percent above its base-period
level. It does not mean every ticket became 10 percent more expensive.

The engine records basket and methodology versions, base-price inputs,
configured and effective weights, every cell contribution, coverage, and
reasons for missing or excluded cells. The base requires seven eligible dates.
Before that, the result remains `PROVISIONAL_BASE`.

## 9. Missing data, outliers, and confidence

- Missing cells never become zero.
- Available weights can be renormalized under the documented prototype policy.
- Coverage stays visible beside the index.
- Unusual fares are flagged and retained rather than automatically erased.
- One-source evidence remains `LOW` confidence even with complete basket cells.

## 10. Provenance: the most important feature

```text
Daily APIx
  -> index component
  -> daily route-window price
  -> canonical fare
  -> normalized fare observation
  -> raw quote
  -> collection job
  -> collection run
  -> source
```

Every layer keeps its relevant parser, normalization, canonicalization, basket,
and methodology version. This makes the result reproducible after rules change.

## 11. Data classes

| Data class | Meaning |
|---|---|
| `SYNTHETIC` | Deterministic invented data for local development and tests. |
| `RECORDED_DEMO` | Permitted recorded or provider sandbox structures. |
| `HISTORICAL` | Imported reference information with named provenance. |
| `LIVE` | Data collected from an approved production source. |

These classes never silently mix. The dashboard displays the active class.

## 12. Source adapters and the exact Duffel answer

### FixtureAdapter

- always available locally;
- needs no internet or external fare API;
- produces deterministic `SYNTHETIC` quotes;
- exercises planning, raw storage, normalization, QA, canonicalization, APIx,
  APIs, exports, and dashboard;
- creates the reliable SIH fallback demonstration.

### DuffelAdapter

- calls Duffel's documented Flights API using authenticated HTTPS;
- requires a backend access token and explicit enable/approval settings;
- stores test-token responses as `RECORDED_DEMO`;
- stores `LIVE` only when configuration and the payload both confirm live mode;
- remains disabled by default and fails closed when configuration is missing.

### PermissionedWebAdapter

- provides the project’s own browser extraction engine;
- requires a versioned profile, explicit approval, saved permission reference,
  and positive robots decision;
- does not bypass CAPTCHA, authentication, blocking, or source restrictions;
- records the exact failure when a page or parser changes.

### Direct answers

**Will the full local application work without Duffel and without any external
airfare API? Yes.** Run the fixture pathway. The complete software pipeline and
dashboard work with local PostgreSQL.

**Is Duffel the automatic fallback? No.** Duffel is the optional documented
real-source adapter. Fixture or permitted recorded-demo data is the fallback
demonstration pathway.

**If Duffel fails, will the system silently use fixture data? No.** It records
the failure. Silent switching would hide the true data origin. The operator
deliberately selects `fixture`, `duffel`, or `permissioned_web`.

## 13. The four dashboard pages

### Overview

Current APIx, daily/weekly/monthly movement, publication status, coverage,
confidence, warnings, history, route coverage, source dispersion, and the
15-cell route/window matrix.

### Route Explorer

Three-route selector, current route index, fare history, carriers, source
dispersion, and lead-time behavior.

### Provenance

Source, run, job, raw quote, normalized value, quality decision, versions, and
index-inclusion status for one observation.

### Operations

Latest run, valid observations, quality score, inclusion rate, source health,
collection history, jobs, and actionable failures. The public UI is read-only.

## 14. What an API means

An API is a set of URLs that software can call. React calls FastAPI and receives
structured JSON. Reviewers can inspect the same endpoints at
`http://localhost:8000/docs`.

```text
GET /api/v1/index/current
GET /api/v1/index/current/coverage
GET /api/v1/index/history
GET /api/v1/index/weekly
GET /api/v1/index/monthly
GET /api/v1/routes
GET /api/v1/routes/{origin}/{destination}/lead-time
GET /api/v1/observations/{id}/provenance
GET /api/v1/collection-runs
GET /api/v1/sources/health
GET /api/v1/quality/summary
```

Administrative POST endpoints require a backend token. Tokens never enter React
or browser storage.

## 15. Main database records

| Record | Purpose |
|---|---|
| Source | Approval, rate, parser, and health identity. |
| Route | One configured origin/destination pair. |
| Collection run | One daily execution and overall status. |
| Collection job | One route, window, and source request. |
| Raw quote | Preserved source evidence and hash. |
| Fare observation | Normalized fare plus QA decision. |
| Canonical fare | Representative price for one physical flight. |
| Daily route-window price | Median input for one basket cell. |
| Daily index/component | APIx and exact contributions. |
| Period index/input | Weekly/monthly result and daily lineage. |
| Historical dataset/observation | Separate back-test evidence. |

Foreign keys and unique constraints preserve lineage and prevent duplicates.
Repeating the same fixture date returns the existing run.

## 16. Reliability and safety

The worker has a finite timeout, at most two retries after the initial attempt,
bounded backoff, source-specific pacing, structured failures, job isolation,
restart-safe attempt budgets, and daily idempotency.

The system never attempts CAPTCHA circumvention, proxy rotation, fingerprint
evasion, or credential misuse. It needs no passenger identity or payment data.

## 17. Historical comparison and exports

Historical imports remain separate from live and synthetic collection. The
pipeline can produce rebased monthly comparisons, deviation, overlap, coverage,
and correlation when the series is suitable.

Exports include fare CSV, daily and period index CSV, back-test CSV, a complete
JSON package, and a six-sheet Excel workbook. Each export states its data class,
generation time, methodology, coverage, and available provenance.

## 18. How to run the complete local demo

```bash
docker compose up -d --build
docker compose ps
```

Open:

- dashboard: `http://localhost:5173`
- interactive API documentation: `http://localhost:8000/docs`
- database readiness: `http://localhost:8000/ready`

Run deterministic local collection when needed:

```bash
make demo
```

Stop without deleting PostgreSQL data:

```bash
docker compose down
```

## 19. Recommended five-minute SIH demonstration

1. Open Overview and identify `SYNTHETIC`, current APIx, coverage, and warning.
2. Explain the fixed three-route, five-window basket.
3. Open Route Explorer and switch to `DEL-BLR`.
4. Explain fare history and the T+45 to T+1 lead-time idea.
5. Open Provenance and select one observation.
6. Follow Source, Raw quote, Normalized observation, QA, and inclusion status.
7. Open Operations and show that failures remain explicit.
8. Open FastAPI `/docs` to prove the dashboard is not reading a prepared file.

The strongest demo sentence is:

> Pick any displayed observation and we can show how it entered, or did not
> enter, the final APIx.

## 20. Verification evidence

The accepted local prototype has:

- 9,392 lines of application code and project scripts;
- 3,572 lines of backend and frontend tests;
- 101 backend tests passed plus four PostgreSQL-specific tests exercised
  separately at the Phase 16 acceptance point;
- five frontend tests passing after the premium redesign;
- clean frontend lint, typecheck, production build, design lint, and strict UI
  audit;
- healthy local PostgreSQL and FastAPI containers;
- browser-verified desktop, tablet, and mobile dashboard views.

These counts describe implementation evidence. They do not replace a genuine
approved live-source run.

## 21. Complete locally and externally gated

### Complete locally

- Phases 0 through 16;
- fixture collection, three routes, and five-window planning;
- raw/normalized storage, QA, deduplication, and canonicalization;
- daily, weekly, and monthly prototype APIx;
- historical/back-test pipeline;
- APIs and CSV/JSON/Excel exports;
- premium responsive React dashboard;
- Docker/PostgreSQL environment and project documentation.

### Implemented but externally gated

- Duffel adapter needs the operator’s credential and approval;
- permissioned web adapter needs written permission and a real profile;
- genuine `LIVE` evidence needs an approved source;
- Azure operation needs provisioned Azure resources.

### Honest limitations

- Three routes do not represent the whole Indian market.
- Equal prototype weights need future subject-matter validation.
- One daily observation is not continuous pricing.
- Local dashboard values are currently synthetic.
- The historical sample validates machinery, not official equivalence.
- APIx is a prototype index, not an official government statistic.

## 22. Questions judges may ask

### Why not scrape every airline continuously?

Continuous scraping weakens comparability and creates legal and operational
risk. The adapter design can add approved sources without changing the engine.

### Why PostgreSQL instead of Excel?

Runs, jobs, raw quotes, observations, canonical fares, components, and versions
form a relational evidence chain. Excel remains a review export.

### Why use a median?

Dynamic fares can contain extreme values. A median gives a transparent, robust
prototype statistic while retaining flagged evidence.

### How do you avoid counting the same flight twice?

The system creates a physical-flight identity and one canonical fare before
aggregation.

### Is React calculating the index?

No. The backend calculates and persists APIx. React displays FastAPI responses.

### What happens when a source fails?

The exact failure is stored, other jobs continue, and no silent data-class
substitution occurs.

### Can the methodology change later?

Yes. The index module, database weights, versioned base prices, and component
lineage keep methodology separate from collection and presentation.

### Why should anyone trust the number?

The reviewer can trace APIx through every component, canonical fare,
observation, raw quote, job, run, and source.

## 23. Documentation map

- `README.md`: setup and operating instructions.
- `PRODUCT.md`: audience, truth boundaries, and success criteria.
- `docs/architecture.md`: modules, topology, and provenance.
- `docs/methodology.md`: basket, base, formula, weights, and limitations.
- `docs/source-policy.md`: sources, data classes, and failure rules.
- `docs/data-dictionary.md`: database entities and fields.
- `docs/api-reference.md`: endpoints and errors.
- `docs/azure-deployment.md`: future Azure procedure.
- `docs/final-acceptance.md`: verification and remaining gates.
- `docs/master-phase-status.md`: Phase 0 through 16 status.
- `DESIGN.md`: premium visual system.
- `UX-CONTRACT.md`: shared behavior and accessibility rules.

## 24. Short explanation to memorize

> Airfare APIx is an auditable Indian airfare statistics prototype. Every day,
> it plans comparable searches for three routes and five advance-booking
> windows. Source adapters produce raw quotes, PostgreSQL preserves the
> evidence, and the backend normalizes, quality-checks, deduplicates, and
> canonicalizes each physical flight. A versioned fixed-basket engine converts
> route-window medians into a prototype index with base 100. FastAPI exposes the
> stored results, while React lets a reviewer trace any number back to its
> source. The complete local demo works without an external airfare API through
> an explicitly labelled synthetic fixture. Duffel is optional and requires
> separate credentials and approval.
