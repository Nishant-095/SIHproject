# Phase 0 — Project Contract Checklist

Status legend:

- `[ ]` Not yet verified
- `[x]` Implemented and verified
- `[!]` Deliberately deferred with a recorded reason

## Scope freeze

- [x] Product is defined as an auditable airfare price-index platform, not a booking or prediction application.
- [x] Level-A MVP boundary and explicitly deferred features are recorded.
- [x] The three MVP routes are frozen.
- [x] The five booking windows are frozen.
- [x] The daily collection time and methodological timezone are frozen.
- [x] The meaning of one raw quote, one normalized observation, one canonical fare, and one APIx value is frozen.

## Sampling and index methodology

- [x] Passenger, journey, cabin, stop, currency, public-access, and optional-add-on rules are frozen.
- [x] Booking-window calculation is unambiguous.
- [x] Same-source duplicates and cross-source observations are treated differently.
- [x] Canonical physical-flight fare selection is defined.
- [x] Route-window daily aggregation is defined.
- [x] Prototype basket weights and base-period construction are defined.
- [x] Missing-data and minimum-coverage rules are defined.
- [x] Quality flags, hard exclusions, and statistical-outlier treatment are defined.
- [x] Prototype methodology is clearly distinguished from an official MoSPI/DGCA index.

## Architecture and provenance

- [x] Lean React + Vite, FastAPI, PostgreSQL architecture is frozen.
- [x] Raw-to-index lineage is documented end to end.
- [x] Module responsibilities and forbidden coupling are documented.
- [x] Live, historical, fixture, and recorded-demo data are kept distinguishable.
- [x] Methodology and parser versioning requirements are recorded.

## Source policy

- [x] Fixture-first development policy is defined.
- [x] A real-source approval gate is defined.
- [x] Rate limiting, terms review, robots handling, and block handling are defined.
- [x] CAPTCHA bypass, credential misuse, and anti-bot circumvention are prohibited.
- [x] Structured source failure codes are defined.
- [x] No real source is falsely claimed as approved before its review is recorded.

## Data contract

- [x] Core entities and important fields are defined.
- [x] Currency uses decimal/numeric storage rather than floating point.
- [x] UTC storage and Asia/Kolkata methodological interpretation are defined.
- [x] Raw evidence is immutable in normal operation and content-hashed.
- [x] Availability states are distinct from source failures.
- [x] Index outputs retain methodology version, coverage, and component lineage.

## Verification

- [x] All four Phase 0 documents agree on routes, windows, time, fare specification, and prototype formula.
- [x] No deferred feature is presented as implemented.
- [x] No unresolved official methodology choice is presented as an official fact.
- [x] Phase 1 entry gate and Phase 0 completion decision are recorded.

## Evidence

Verified on 2026-09-05:

- `architecture.md` freezes the Level-A boundary, lean runtime, ownership boundaries, provenance chain, and Phase 1 entry gate.
- `methodology.md` freezes the routes, windows, 10:00 Asia/Kolkata schedule, fare specification, canonicalization, seven-day base, fixed `1/15` weights, no-imputation policy, and 80% publication threshold.
- `source-policy.md` freezes fixture-first delivery, the real-source approval record, bounded retries, prohibited behaviour, failure codes, evidence retention, and demo labelling.
- `data-dictionary.md` freezes relational entities, fields, enums, constraints, decimal money, UTC/date semantics, content hashing, version fields, and raw-to-index lineage.
- Cross-document search confirmed all three routes, all five windows, the daily schedule, data classes, canonicalization version, methodology version, basket weight, and coverage threshold.
- Cross-document search found no Next.js architecture reference; the frontend contract is React + Vite + TypeScript.
- The exact real provider remains correctly unapproved until the Phase 4 current-source review. This is an enforced approval boundary, not an incomplete Phase 0 decision.

## Completion decision

**PHASE 0: COMPLETE**

Phase 1 may begin. It must implement the frozen lean foundation without adding
deferred infrastructure or changing methodology silently.
