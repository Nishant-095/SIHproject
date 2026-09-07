# SIH26056 Airfare APIx — Source Collection Policy

**Status:** Phase 0 policy with Phase 4 API and permissioned-web paths  
**Policy version:** `source-policy-v0.3.0`  
**Effective date:** 2026-09-05

## 1. Purpose

This policy governs which fare sources may be used and how collection behaves.
The goal is reproducible fare observation without bypassing access controls,
misrepresenting data, or making the system dependent on one provider.

## 2. Source priority

Sources are considered in this order:

1. documented public or partner API/feed whose terms permit the intended use;
2. data provided with written authorization;
3. a normal public HTTP response only after terms and robots review permits the
   collection pattern;
4. browser automation only when normal public interaction is permitted and no
   control must be bypassed;
5. fixture or permitted recorded response for development and demonstration.

The easier technical method does not override legal, contractual, ethical, or
access restrictions.

## 3. Phase-specific source strategy

- Phase 2–3 uses `FixtureAdapter` to prove the complete pipeline without
  external dependency.
- Phase 4 selects exactly one real candidate and completes the approval record
  before enabling live collection.
- A second source is attempted only after the first source and core pipeline
  pass their gates.
- The exact real provider is intentionally not declared approved in Phase 0.
  Approval depends on the provider's current documentation, terms, access
  method, and credentials at implementation time.

This is a frozen strategy, not a claim that any unnamed website may be scraped.

### Phase 4 selected integration

Duffel's documented Flights API is the first real technical adapter. The
review record is `docs/source-reviews/duffel.md`. It is seeded disabled and
pending operational approval. A backend token, current account-agreement
review, and explicit enablement are required before any external request.

Duffel sandbox responses are `RECORDED_DEMO`; only a production response that
explicitly declares `live_mode=true` may enter a `LIVE` run. The system does
not fall back to website scraping when the API is unavailable.

### Permissioned web collection path

The project also contains a small provider-neutral browser extraction engine
for the scraping/extraction capability named by SIH26056. It is not bound to an
airline by default. The review record is
`docs/source-reviews/web-collection-candidates.md`.

It fails closed unless all of `WEB_SOURCE_PROFILE_PATH`,
`WEB_SOURCE_ENABLED=true`, `WEB_SOURCE_APPROVED=true`, and a non-empty
`WEB_SOURCE_PERMISSION_REFERENCE` are supplied. It then checks `robots.txt`,
honors crawl delay, restricts navigation to the approved origin, and stops on
CAPTCHA or block pages. Extraction rules are declarative JSON, so adding an
approved source does not duplicate the collection pipeline.

## 4. Source approval states

| Status | Meaning | Collection allowed? |
|---|---|---:|
| `PENDING_REVIEW` | Candidate identified; review incomplete | No |
| `APPROVED` | Evidence supports the configured collection method | Yes |
| `RESTRICTED` | Terms, robots, access control, or written direction disallows it | No |
| `BLOCKED` | Source actively prevents the permitted method | No retries beyond policy |
| `PARSER_CHANGED` | Returned structure no longer matches verified fixtures | No index ingestion |
| `DISABLED` | Operator intentionally disabled the source | No |

Only `APPROVED` sources may create `LIVE` observations eligible for APIx.

## 5. Required approval record

Before a real source is enabled, record:

- source name and type;
- base URL and exact endpoint/page scope;
- collection method;
- public documentation URL, terms URL, and robots URL where applicable;
- review date and reviewer;
- authentication requirements;
- permitted data and retention restrictions;
- configured request rate and concurrency;
- raw-payload retention decision;
- attribution requirements;
- known access controls;
- approval state and concise rationale.

Because source rules can change, the record must be rechecked before a major
demo or production release.

## 6. Prohibited behaviour

The project must never implement:

- CAPTCHA solving or bypass;
- credential theft, sharing, or unauthorised account use;
- proxy rotation intended to evade a block;
- browser fingerprint or automation-evasion systems;
- hidden endpoint abuse contrary to documented permission;
- robots or terms bypass;
- rate-limit evasion;
- fabricated quotes or failures presented as live observations.

When a permitted collection path is blocked, record `CAPTCHA_BLOCKED`,
`TERMS_RESTRICTED`, `ROBOTS_DISALLOWED`, or another accurate status and move on.

## 7. Rate and retry policy

- Each approved source has configurable requests-per-minute and concurrency.
- MVP default concurrency is one request per source unless approval explicitly
  supports more.
- A job has a finite timeout and no more than two automatic retries.
- Retries use bounded backoff and apply only to transient failures.
- `TERMS_RESTRICTED`, `ROBOTS_DISALLOWED`, `CAPTCHA_BLOCKED`, and confirmed
  `PARSER_CHANGED` are not aggressively retried.
- Repeated failures degrade or disable the source without stopping other jobs.

Exact numeric request limits are source-specific and may not exceed the
documented or approved limit.

## 8. Standard adapter contract

Every adapter accepts the same logical request:

```text
origin
destination
travel_date
passenger_count = 1
cabin = ECONOMY
nonstop_preference = REQUIRED_FOR_INDEX
currency = INR
```

It returns raw quotes or a structured failure. An adapter may:

- make an approved source request;
- parse source-shaped fields;
- return raw quote objects;
- expose parser version and structured failures.

It may not:

- calculate APIx;
- decide cross-source canonical fares;
- change weights or basket membership;
- write frontend-specific structures;
- silently fabricate or repair missing source values.

## 9. Failure codes

Adapters and jobs use these codes:

```text
SOURCE_UNAVAILABLE
RATE_LIMITED
ROBOTS_DISALLOWED
TERMS_RESTRICTED
CAPTCHA_BLOCKED
AUTHENTICATION_FAILED
PARSER_CHANGED
NO_RESULTS
NETWORK_TIMEOUT
INVALID_RESPONSE
UNKNOWN_ERROR
```

`NO_RESULTS` means a valid source response contained no matching itinerary.
It is not automatically `SOLD_OUT`. `SOURCE_UNAVAILABLE` and other technical
failures are never interpreted as market availability.

## 10. Raw evidence policy

Store the smallest permitted evidence sufficient for reproducibility:

- query fields;
- source identifier;
- actual UTC observation timestamp;
- raw fare and flight fields;
- compact permitted JSON representation;
- parser version;
- content hash.

Do not retain complete pages, personal data, tokens, cookies, or credentials.
If larger snapshots are later permitted and needed, keep them outside the
database and store only their path, hash, media type, and retention metadata.

## 11. Parser change protection

Each real adapter requires permitted representative fixtures covering:

- normal results;
- no results;
- missing optional fields;
- malformed or unexpected response.

Parsing failures must fail closed: the affected record does not enter the
index. A changed structure records `PARSER_CHANGED` rather than silently
producing zero or incorrect fares.

## 12. Demo policy

The application supports:

- `LIVE` mode using currently approved sources;
- `RECORDED_DEMO` mode using clearly labelled, permitted recorded structures;
- `SYNTHETIC` mode for tests and development.

The dashboard must show the mode. Recorded or synthetic results may demonstrate
the pipeline but may never be described as fares collected live during the
demo.

## 13. Definition of done for a real adapter

A real adapter is complete only when:

- the approval record is complete and status is `APPROVED`;
- the common interface is implemented;
- normal, empty, timeout, invalid, and blocked cases are handled;
- raw evidence is stored within policy;
- parser fixtures and tests pass;
- request rate and retries are configured;
- failures appear in run and source health;
- one genuine quote completes the raw-to-normalized path.
