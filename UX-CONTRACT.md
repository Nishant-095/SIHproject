# Airfare APIx UX Contract

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Native `select` for the narrow mobile route picker; semantic button group for the three-position desktop board | `DESIGN.md` and this contract | native mobile / authored button group desktop | keyboard, label association, route-switch component test, desktop and narrow browser inspection |
| Scrollbar | Global application stylesheet | `DESIGN.md` and `frontend/src/styles.css` | document / labelled table overflow / observation-list overflow | computed overflow and desktop, tablet, phone browser inspection |
| Data state | Shared `DataState` component | this contract and `frontend/src/components/DataState.tsx` | loading / error with retry / empty / ready | component tests and live success/loading inspection |
| Navigation | Shared `AppShell` links and route-title owner | this contract and `frontend/src/App.tsx` | desktop rail / compact rail / mobile bottom strip | keyboard, direct route, 404, and breakpoint inspection |

## Authoritative sources

| Concern | Source | UI consequence |
|---|---|---|
| Index, coverage, data class, route and observation schema | `backend/app/api/routes.py`, `frontend/src/api.ts` | Values are rendered from the public API; missing values remain explicit. |
| Index methodology and publication boundary | `docs/methodology.md` | Coverage, confidence, missing-data policy, versions, and publication state stay visible. |
| Source and data-class policy | `docs/source-policy.md` | Synthetic/recorded/live classification is never hidden or restyled as live. |
| Public versus protected operations | API route dependencies and `docs/deployment-runbook.md` | React operations is read-only; protected mutations are not exposed. |

## Canonical flows

| Flow | Entry | Success | Loading/error/empty | Focus/restoration |
|---|---|---|---|---|
| Read national APIx | `/` | Current instrument and evidence tables | Stable loader, persistent Retry, explicit empty copy | Route heading receives programmatic focus. |
| Compare a route | `/routes` | Selected route, history and lead-time evidence update | Existing data-state boundary remains active | Desktop board buttons and mobile native select keep native keyboard behavior. |
| Inspect provenance | `/provenance` | Selected observation reveals adjacent evidence spine | List and detail report states separately | Selected observation stays in the master list; no modal trap. |
| Review operations | `/operations` | Readiness, quality, health and jobs are visible | Each remote region retains recovery state | Read-only navigation; no destructive action. |

## Cross-screen invariants

- App navigation and the evidence-boundary statement remain available on every
  route, including the app-owned 404 page.
- `SYNTHETIC`, `RECORDED_DEMO`, `HISTORICAL`, and `LIVE` retain their API meaning.
- No missing fare, source, or basket cell is presented as zero.
- The document owns vertical scrolling; table and observation regions own only
  the local overflow they require.
- Animations are presentation-only, cleaned up on unmount, and disabled by the
  reduced-motion preference.
- Dates, INR, and methodology time use the shared formatting functions.
