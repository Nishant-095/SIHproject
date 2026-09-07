# Original Phase 4–7 Implementation Checklist

**Created before implementation:** 2026-09-05  
**Rule:** mark an item complete only after code plus direct test evidence exists.

Status:

- `[ ]` Not verified
- `[x]` Implemented and verified
- `[!]` Implemented but external credential/production verification is pending

## Phase 4 — First real adapter

- [x] Select one currently documented airfare API rather than scraping an undocumented website.
- [x] Record provider, endpoint, authentication, terms, rate, retention, attribution, and review evidence.
- [x] Keep the real source disabled unless its credential and explicit enablement are configured.
- [x] Keep test/sandbox results out of the `LIVE` data class.
- [x] Implement the common adapter interface without changing the planner contract.
- [x] Send the frozen one-adult, one-way, economy search request.
- [x] Filter or reject connecting itineraries for index eligibility.
- [x] Parse normal offers into source-shaped raw quotes without inventing fare components.
- [x] Handle empty results, authentication failure, rate limit, timeout, unavailable source, and malformed responses.
- [x] Retain only compact permitted evidence without tokens or personal data.
- [x] Add sanitized fixtures for normal, empty, missing-optional, and malformed responses.
- [x] Add adapter contract and parser tests.
- [x] Add a provider-neutral Playwright extraction adapter driven by a small versioned JSON profile.
- [x] Require explicit written-permission evidence before any browser request.
- [x] Enforce same-origin URLs/redirects, robots decisions, crawl delay, and a low configured source rate.
- [x] Stop on CAPTCHA/block pages without bypass, proxy rotation, or fingerprint evasion.
- [x] Prove JavaScript rendering and field extraction with a real local Chromium page.
- [x] Prove the web path through 15 jobs and raw, normalized, and canonical PostgreSQL rows.
- [!] Bind the engine to a genuine airline/OTA. Reviewed candidates require written permission, so it remains disabled and unbound.
- [!] Prove one credentialed production quote through raw storage and normalization. The parser and pipeline are verified with hand-authored, source-shaped contract fixtures; a user-owned activated account and token are still required for a genuine production observation.

## Phase 5 — Five-window planner

- [x] Preserve exact T+1, T+7, T+15, T+30, and T+45 planning.
- [x] Preserve exactly 15 jobs per enabled source for three routes and five windows.
- [x] Plan fixture, recorded-demo, and live runs without mixing data classes.
- [x] Preserve run and job idempotency, including recovery of interrupted planned/running jobs.
- [x] Re-run planner and migration tests after the Phase 4–7 changes.

## Phase 6 — Scheduler and worker reliability

- [x] Add a reusable collection worker/service boundary independent of APScheduler.
- [x] Enforce a configurable finite timeout per adapter call.
- [x] Add at most two automatic retries after the first attempt.
- [x] Use bounded exponential backoff with no sleep after the final attempt.
- [x] Retry only transient source-unavailable, rate-limit, timeout, and unknown failures.
- [x] Never retry policy, authentication, parser-change, invalid-response, CAPTCHA, or no-result outcomes.
- [x] Persist the final attempt count and structured terminal failure.
- [x] Keep one failed job isolated from unrelated jobs.
- [x] Make scheduled runs choose an explicitly configured source/data class.
- [x] Prevent overlapping scheduled runs and preserve daily idempotency.
- [x] Test success-after-retry, retry exhaustion, non-retryable failure, timeout, restart recovery, and failure isolation.

## Phase 7 — Normalization and QA completion

- [x] Add maintained airport aliases for the frozen route basket and reject unknown/non-matching endpoints.
- [x] Add a maintainable Indian carrier alias/code dictionary beyond fixture-only names.
- [x] Normalize carrier code, carrier name, flight number, local times, currency, cabin, and fare components.
- [x] Preserve unavailable components as null rather than fabricating a decomposition.
- [x] Enforce non-negative monetary values and total/component consistency.
- [x] Preserve malformed and normalization-rejected raw evidence with an explainable excluded observation.
- [x] Preserve reproducible flight identity.
- [x] Detect duplicates within one source/job.
- [x] Flag statistical price outliers deterministically without silently deleting them.
- [x] Add a canonical cross-source fare table keyed by run, route/window, flight identity, and observed fare specification.
- [x] Link eligible observations to a canonical fare without deleting source evidence.
- [x] Flag same-source duplicates and cross-source price conflicts explicitly.
- [x] Choose a deterministic representative price while retaining min, max, source count, and dispersion.
- [x] Make the representative-fare policy configurable between direct-first and approved-source median rules.
- [x] Keep ineligible observations out of canonical/index-ready fares.
- [x] Expose per-source health, failures, success rate, latency, parser version, and last success/failure.
- [x] Add route/carrier query indexes used by Phase 7 inspection paths.
- [x] Add migration, normalization, duplicate, canonicalization, and provenance tests.

## Verification gate

- [x] Ruff passes.
- [x] mypy passes.
- [x] Complete backend tests pass: 80 passed, including real Chromium extraction and real PostgreSQL integration tests.
- [x] PostgreSQL Alembic upgrade, drift check, downgrade, and re-upgrade pass.
- [x] PostgreSQL 17.11 Docker runtime is healthy and persists data across container restarts.
- [x] One fixture run produces 15 successful jobs, 30 valid observations, and 30 canonical fares; a repeat creates no duplicates.
- [x] Three distinct scheduled fixture dates produce 45 successful PostgreSQL jobs without overlap or cross-date duplication.
- [x] Duffel contract fixtures prove parser behavior; they are not represented as captured production data.
- [x] No real credential or access token is present; compact stored evidence contains no traveller identity fields.
- [x] Master Phase 0–16 tracker is updated from the final evidence.

## Completion evidence

Verified on 2026-09-05 with the repository's lint, typecheck, backend, frontend,
build, live PostgreSQL migration, fixture-run, restart-persistence, and adapter-contract checks. All
Phase 5, 6, and 7 implementation items are complete. Phase 4 code and
contract-fixture plus permissioned-web engine integration are complete. The final production
gate remains external-pending because no user-owned activated Duffel live credential or
written airline/OTA browser-collection permission was available.
