# Airfare APIx — Product Context

**Status:** implemented prototype context  
**Last reviewed:** 2026-09-06

## Product truth

Airfare APIx is an evidence-first statistical operations console for a
prototype Indian domestic airfare price index. It collects comparable fares on
a controlled schedule, retains the raw evidence, applies explicit quality and
canonicalization rules, calculates a versioned index, and lets a reviewer trace
an index value back to the source quote.

It is not an airline-booking product, a price predictor, an official Government
of India statistic, or a claim that the whole Indian market is represented.

## Primary users and jobs

| User | Primary job |
|---|---|
| Hackathon judge | Establish quickly that the solution is real, coherent, and not a mock dashboard. |
| Statistical reviewer | Inspect basket, coverage, missing-data rules, versions, and calculation lineage. |
| Data/operations reviewer | See collection health, failures, source state, and raw-to-index provenance. |
| Student maintainer | Run and explain the system without operating a large distributed platform. |

## Implemented capabilities

- fixed three-route by five-booking-window MVP basket;
- fixture, Duffel, and explicitly permissioned browser-adapter contracts;
- scheduled and manually triggered bounded collection workers;
- PostgreSQL raw quotes, normalized observations, canonical fares, and lineage;
- deterministic daily APIx plus weekly/monthly aggregation and coverage labels;
- historical reference import and a labelled 30-day synthetic back-test path;
- public read APIs, protected administration APIs, CSV/JSON/Excel exports;
- four-page React dashboard for index, routes, provenance, and operations.

## Non-negotiable constraints

- React + Vite; do not migrate to Next.js.
- Keep the modular monolith; add infrastructure only for a measured need.
- Keep `LIVE`, `HISTORICAL`, `SYNTHETIC`, and `RECORDED_DEMO` separate.
- Never call fixture/test data live.
- Never bypass CAPTCHAs, robots restrictions, rate limits, or source permission.
- Preserve raw evidence and version identifiers through every derived result.
- Administrative secrets stay server-side and out of the frontend bundle.
- English `en-IN`, India time, INR, laptop-first with usable mobile layouts.

## Product success

A reviewer should be able to answer these questions from the interface and API:

1. What does the current APIx value mean?
2. Which route/window cells contributed, and what coverage was available?
3. Which observations and raw source records produced a selected value?
4. What was excluded, why, and under which methodology/parser version?
5. Is the evidence live, historical, synthetic, or recorded demonstration data?
6. Are sources and scheduled collection healthy?

## Current evidence boundary

The complete application path is locally verified using PostgreSQL-backed
synthetic/fixture data. A genuine `LIVE` observation still requires an approved
production credential or written permission for a configured source. Azure is
documented as a deployment target but has not been provisioned or verified.

## Experience principles

- Evidence precedes decoration.
- Density should help comparison, not create a wall of identical cards.
- The visual language must belong to aviation operations and statistical
  measurement, not generic SaaS or consumer travel booking.
- Motion should explain route changes, calculation lineage, and data updates.
- Keyboard access, visible focus, readable contrast, reduced motion, semantic
  tables, and non-colour status labels are acceptance requirements.

