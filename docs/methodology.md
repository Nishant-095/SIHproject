# SIH26056 Airfare APIx — Prototype Methodology Contract

**Status:** Phase 0 frozen contract; Phase 8 implementation verified  
**Methodology version:** `prototype-v0.1.0`  
**Effective date:** 2026-09-05

## 1. Statistical purpose and limitation

APIx measures the change over time in a fixed MVP basket of comparable Indian
domestic airfare observations. It is an engineering prototype for transparent
collection, calculation, and auditability.

It is not an official MoSPI or DGCA statistic, is not yet nationally
representative, and must be labelled **Prototype APIx** everywhere it is shown.
No claim of official validation may be made until a documented external
validation phase is completed.

## 2. Frozen MVP basket

### Routes

| Route | MVP reason | Route weight |
|---|---|---:|
| `DEL-BOM` | Canonical north-west trunk example | 1/3 |
| `DEL-BLR` | Canonical north-south trunk example | 1/3 |
| `BOM-BLR` | Canonical west-south trunk example | 1/3 |

These routes are the canonical implementation examples supplied for the MVP.
They provide a compact demonstration across three large aviation markets, but
they are not asserted to represent all Indian air travel. National weights and
route selection remain a later evidence-based methodology task.

### Booking windows

Each route has five equally weighted advance windows:

| Code | Target travel date | Window weight within route |
|---|---:|---:|
| `T1` | observation date + 1 day | 1/5 |
| `T7` | observation date + 7 days | 1/5 |
| `T15` | observation date + 15 days | 1/5 |
| `T30` | observation date + 30 days | 1/5 |
| `T45` | observation date + 45 days | 1/5 |

The MVP therefore contains 15 equally weighted route-window basket items. Each
item has a fixed total basket weight of `1/15`.

Weights are versioned data/configuration, never constants embedded inside an
adapter or UI component.

## 3. Observation schedule

- Official MVP observation time: **10:00 Asia/Kolkata daily**.
- The methodological observation date is the calendar date in
  `Asia/Kolkata` when the run is scheduled.
- Event timestamps are stored in UTC.
- `travel_date` is a local airport-service date, not a UTC timestamp.
- `advance_days = travel_date - methodological_observation_date`.
- `advance_window` is assigned from the exact values 1, 7, 15, 30, and 45;
  all other values are `OTHER` and are not eligible for the fixed MVP basket.

A delayed run retains its planned methodological observation date and records
its actual collection timestamp. Delays are visible in collection health; they
are not silently moved to another window.

“Real-time” in this project means current fares collected by a running system
on this controlled schedule. It does not mean continuous or second-by-second
scraping.

## 4. Frozen fare specification

An eligible quote represents:

```text
one adult
one-way journey
economy cabin
non-stop flight
publicly accessible price
INR
lowest publicly bookable economy offer for that flight at that source
mandatory taxes and source-known mandatory fees included
optional products excluded
```

Additional rules:

- No member-only, corporate, student, armed-forces, senior-citizen, loyalty,
  coupon, wallet, or logged-in personalised discount is eligible.
- Optional seats, meals, extra baggage, insurance, donations, carbon products,
  and flexible-travel add-ons are excluded.
- A payment-method fee shown only after choosing a particular optional payment
  method is excluded. A universally unavoidable fee must be included when the
  source exposes it.
- Fare-family text, included baggage, refundability, and availability are
  recorded when exposed. The MVP selects the lowest eligible public economy
  offer and does not claim identical ancillary benefits across airlines.
- A connecting itinerary is stored and flagged `CONNECTING_FLIGHT`, but is not
  eligible for the MVP index.
- Currency other than INR is retained and flagged, not silently converted.

`total_fare` means the best source-visible total meeting these rules. If the
source does not expose enough information to establish a comparable total, the
quote remains evidence but is excluded with an explicit quality reason.

## 5. Meaning of each data level

### Raw quote

One source-returned airfare record for a specific query and candidate flight,
preserved before common normalization. It includes raw text/payload, query
values, source, actual observation time, and parser version.

### Normalized observation

One source-specific interpretation of a raw quote for a route, scheduled
flight, travel date, fare specification, and observation event. Different
sources quoting the same physical flight remain different observations.

### Canonical fare

The single fare value chosen for one physical flight and observation event
after comparing its eligible source-specific observations. It prevents a
flight from receiving more influence merely because it appears on more OTAs.

### Daily route-window price

The median of eligible canonical physical-flight fares for one route, booking
window, and methodological observation date.

### Daily APIx

A fixed-weight aggregation of available route-window price relatives for one
methodological observation date, accompanied by coverage and methodology
version.

## 6. Physical-flight identity

Identity is the hash of this canonical string:

```text
carrier_code|flight_number|origin_iata|destination_iata|travel_date|scheduled_departure_local
```

Example:

```text
6E|1234|DEL|BOM|2026-09-12|09:20
```

The identity input is stored as well as its hash so a reviewer can reproduce
the result. Missing identity fields prevent cross-source canonicalization and
exclude the observation from the prototype index.

## 7. Duplicate and cross-source rules

### True duplicate

The same source produces the same logical quote more than once for the same
collection job. The first successfully stored raw record remains evidence;
later repetitions are marked `DUPLICATE` and excluded from aggregation.

### Same flight, different source

These are independent source observations and are never deleted as duplicates.
All are retained. Canonicalization chooses one flight-level value by the
versioned policy below.

## 8. Canonical-fare policy

Policy version: `direct-then-median-v1`.

For one physical flight in one observation event:

1. consider only observations passing hard eligibility checks;
2. if an approved direct-airline source has an eligible quote, select that
   source's quote;
3. if several eligible direct-airline quotes exist, use their median;
4. otherwise use the median of eligible approved-source quotes;
5. retain the contributing and rejected observation identifiers and selection
   reason.

Fixture, synthetic, historical, and recorded-demo observations are never mixed
with live observations during canonicalization.

## 9. Quality and eligibility

### Hard exclusions

An observation is excluded when any of these applies:

- missing or non-positive total fare;
- `total_fare < taxes` where both are known;
- invalid route, travel date, or exact MVP booking window;
- unsupported or unknown currency;
- unsupported cabin or connecting itinerary;
- incomplete physical-flight identity;
- parser error or fare-component mismatch that prevents a reliable total;
- duplicate from the same source job;
- data-class mismatch with the series being calculated;
- source not approved for live collection.

### Statistical outliers

Route-window distributions may use median absolute deviation or IQR to attach
`POSSIBLE_OUTLIER`. A statistical outlier is not automatically excluded because
real demand surges are valid airfare behaviour. Exclusion requires a separate
hard validation failure or an auditable manual decision.

### Quality score

An optional 0–100 operational score may summarize completeness, valid money,
identity, fare specification, source confidence, and cross-source agreement.
It is not a probability or statistical confidence interval and does not replace
explicit flags.

## 10. Base period

For each of the 15 basket items, the prototype base price is:

> the median daily route-window price across the first seven eligible scheduled
> LIVE collection dates in the declared base-period version.

Rules:

- A basket item needs seven eligible daily prices before its live base price is
  frozen.
- The exact seven dates and underlying aggregate identifiers are retained.
- A fixed seeded base may be used for synthetic or recorded-demo mode, but must
  be labelled with that data class.
- A new base creates a new basket/base version; historical published values are
  not silently rewritten.

## 11. APIx calculation

For basket item `i` on date `t`:

```text
R(i,t) = 100 * P(i,t) / B(i)
```

where:

- `P(i,t)` is the daily route-window median fare;
- `B(i)` is its frozen base-period median fare.

The daily prototype APIx is:

```text
APIx(t) = sum(w(i) * R(i,t)) / sum(w(i)), for available eligible items
```

The fixed `w(i)` is `1/15` for every MVP item. Renormalization occurs only over
available eligible items and is always accompanied by coverage:

```text
coverage(t) = 100 * sum(available w(i)) / sum(all basket w(i))
```

Publication rules:

- `coverage >= 80%`: publish the daily prototype APIx with its exact coverage;
- `coverage < 80%`: store the calculation as insufficient coverage and do not
  present it as the headline daily APIx;
- no fare imputation is performed in the MVP;
- route-level results follow the same rule across their five windows;
- money and index calculations use decimal arithmetic;
- persisted display values may be rounded to two decimal places only after the
  full-precision calculation.

## 12. Longitudinal lead-time curve

A lead-time curve follows the same physical departure date and, where
possible, physical flight as it is observed from farther to nearer departure.
For example, the system may connect its `T45`, `T30`, `T15`, `T7`, and `T1`
observations. Missing points remain missing; the UI does not interpolate or
invent them.

### Weekly and monthly aggregation

Policy version: `published-days-mean-no-imputation-v1`.

- A weekly period is Monday through Sunday; a monthly period follows the
  calendar month.
- The period APIx is the arithmetic mean of its available `PUBLISHED` daily
  APIx values. `PROVISIONAL_BASE` and `INSUFFICIENT_COVERAGE` daily rows are
  retained as lineage but excluded from the value.
- Missing days and missing values are never imputed. The result records the
  expected, observed, valued, and low-coverage day counts.
- Average and minimum daily coverage, distinct contributing source count,
  aggregation status, confidence, and warning codes are stored with the value.
- A period remains `PARTIAL` until all expected daily values are present. Any
  observed low-coverage day makes its status `INSUFFICIENT_COVERAGE`; an absent
  published value is `NO_DATA` rather than zero.
- `HIGH` confidence requires a complete period, at least 95% average coverage,
  and at least two contributing sources. Single-source and incomplete periods
  are explicitly labelled `LOW`, `MEDIUM`, or `INSUFFICIENT` by the stored
  rules; these labels are operational metadata, not confidence intervals.

## 13. Reproducibility requirements

### Historical comparison and back-test

Policy version: `first-overlap-rebase-100-v1`.

- Imported reference values remain `HISTORICAL` and retain dataset publisher,
  source URL, licence, metric, base period, content hash, source record ID,
  publication status, and raw record metadata.
- The internal monthly APIx uses the Phase 13 no-imputation aggregate. Only
  months with both an internal value and a national reference value are used.
- Both series are rebased to 100 at their first common month before deviation
  or correlation is calculated. This compares movement, not unlike original
  base levels.
- Point deviation is `internal_rebased - reference_rebased`; percentage
  deviation divides that value by the rebased reference.
- Pearson correlation requires at least three common months and variation in
  both series. Otherwise the output explicitly states
  `INSUFFICIENT_OVERLAP` or `CONSTANT_SERIES`.
- Route-level rows compare each route's weighted monthly price relatives with
  the overall monthly APIx and report observed/expected-day coverage.
- The bundled 30-day scenario is synthetic engineering evidence. It does not
  establish official validity or national representativeness.

Every index result stores or links to:

- methodological observation date;
- data class;
- basket version;
- base-period version;
- methodology version;
- canonicalization policy version;
- component prices, weights, relatives, and contributions;
- coverage and publication status;
- calculation timestamp.

Given the retained inputs and code version, recalculation must reproduce the
same result exactly.

## 14. Known MVP limitations

- Three routes and equal weights are illustrative, not nationally
  representative.
- The lowest public economy fare can contain different ancillary benefits.
- A single daily snapshot does not measure intraday volatility.
- Source availability can affect coverage.
- The seven-day base is a prototype engineering choice, not an official base
  period.
- No seasonal adjustment, imputation, expenditure weighting, or official
  back-testing is claimed.

These limitations must appear in methodology-facing UI or documentation.

## 15. Change control

Changing routes, weights, base dates, eligibility, canonicalization, missing
data, or aggregation creates a new methodology or basket version. Previously
published results remain associated with their original version.
