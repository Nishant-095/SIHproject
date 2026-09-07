# Final Prototype Acceptance Record

**Acceptance date:** 2026-09-06  
**Scope:** Phases 0–16 code and documentation, using local Docker + PostgreSQL  
**Result:** accepted as a complete synthetic-data prototype; external live-data
and Azure operating evidence remain explicitly open

## Acceptance meanings

- **Implemented:** code or documentation exists in this workspace.
- **Verified:** exercised in the current local PostgreSQL/Docker environment.
- **External gate:** requires a credential, permission, subscription, or hosted
  resource that is not present locally.

## Product acceptance

| Requirement | Status | Evidence |
|---|---|---|
| Frozen 3-route × 5-window basket | ✅ Verified | Seeded routes, planner, API, and dashboard matrix |
| Raw quote through index provenance | ✅ Verified | PostgreSQL relations and provenance API |
| Deterministic APIx and base/version rules | ✅ Verified | Unit and PostgreSQL integration tests |
| Daily plus weekly/monthly evidence | ✅ Verified | API, persistence, confidence/warning fields |
| Historical comparison and back-test path | ✅ Verified | Provenance-aware import and 30-day synthetic scenario |
| CSV, JSON, and Excel exports | ✅ Verified | Export tests and six-sheet workbook inspection |
| Premium four-page React dashboard | ✅ Verified | Desktop, tablet, mobile, route-switch, chart, and frontend-test evidence |
| Real-source adapter architecture | ✅ Implemented | Duffel and permission-gated browser adapters share the collector contract |
| Genuine current production observation | 🟡 External gate | Needs approved production credential or written source permission |
| Azure production deployment | ⚪ Not performed | Deployment procedure exists; subscription resources are intentionally absent |

## Automated verification

Run from the project root:

```bash
make lint
make typecheck
make test
make build
```

Current acceptance result:

- backend lint: pass;
- frontend lint: pass;
- backend type check: pass;
- frontend type check: pass;
- backend test suite: **101 passed, 4 skipped** (the four PostgreSQL-marked
  cases are also executed separately against PostgreSQL);
- frontend test suite: **5 passed**;
- frontend production build: pass;
- PostgreSQL-specific integration set: **4 passed**;
- migration head: `20260906_0007`;
- migration/schema drift check: **no new upgrade operations detected**.

Exact counts and the final command transcript are captured during Phase 16 and
summarized in `docs/phase-16-completion-checklist.md`.

## Runtime smoke acceptance

The local Docker services must report:

```text
postgres: healthy
backend: healthy
frontend: running
GET /health: HTTP 200, status ok
GET /ready: HTTP 200, database connected
```

The dashboard must load its data from `http://localhost:8000` and display the
active data class. Current premium visual evidence:

- [`screenshots/premium-overview-desktop.png`](screenshots/premium-overview-desktop.png)
- [`screenshots/premium-overview-tablet.png`](screenshots/premium-overview-tablet.png)
- [`screenshots/premium-overview-mobile.png`](screenshots/premium-overview-mobile.png)
- [`screenshots/premium-route-explorer-desktop.png`](screenshots/premium-route-explorer-desktop.png)

These screenshots validate the implemented Flight Recorder / Index Exchange
interface against the live local API.

## Manual reviewer path

1. Open `http://localhost:5173` and confirm `SYNTHETIC` is visible.
2. On Overview, inspect current APIx, coverage, warnings, history, and the
   15-cell route/window matrix.
3. On Route explorer, switch among all three routes and inspect fare history,
   lead-time data, carriers, and source dispersion.
4. On Provenance, select an observation and follow source/run/job/raw/
   normalized fields.
5. On Operations, inspect readiness, collection runs, source health history,
   and failure details.
6. Open `http://localhost:8000/docs` and exercise one public read endpoint.
7. Download `analysis.xlsx` and confirm the six sheets and metadata/data-class
   labels.

## Failure-state acceptance

- unavailable PostgreSQL makes `/ready` fail rather than report ready;
- missing index data returns an honest empty/not-found state, not zero;
- low coverage and provisional base states remain labelled;
- unknown routes/observations/datasets return `404`;
- invalid query/body data returns `422`;
- missing/wrong admin token rejects mutations;
- an unapproved source cannot be enabled;
- a real adapter without permission/configuration refuses before collection;
- source/normalization failure evidence is retained and not rewritten as sold
  out or as an eligible zero fare.

## Security and data-boundary acceptance

- `.env` and credentials are not frontend inputs;
- the admin token is server-side only;
- CORS is explicit;
- PostgreSQL is bound to loopback in local Docker;
- source policies prohibit anti-bot bypass;
- synthetic, recorded, historical, and live data remain separate;
- no personal traveller information is required or collected.

## Known limitations accepted for the prototype

1. Three routes and equal weights demonstrate the engine but do not represent
   the entire Indian airfare market.
2. One daily observation time is not continuous/second-by-second collection.
3. The locally verified series is synthetic; no genuine live fare is claimed.
4. Cross-source confidence remains limited until approved production sources
   contribute overlapping observations.
5. The historical sample validates the comparison machinery, not statistical
   equivalence with an official national index.
6. Azure performance, availability, TLS connectivity, backup restore, and cost
   are unverified until an actual deployment is authorized.
7. The premium dashboard is locally verified; accessibility certification and
   external user testing remain outside the prototype evidence.

## Final decision

Phase 16 is complete because documentation, API examples, deployment procedure,
and acceptance evidence now exist. The complete local synthetic prototype is
accepted. The following are not silently converted into Phase 16 failures:

- **Phase 4 external evidence:** still needs a genuine approved source run.
- **Azure operating evidence:** still needs the user to authorize/provision an
  Azure subscription deployment.
- **Premium visual redesign:** implemented after the Phase 16 documentation
  boundary and recorded in the maintained design and UX contracts.
