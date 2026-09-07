# Source Review — Duffel Flights API

**Review date:** 2026-09-05  
**Technical reviewer:** Codex implementation audit for the project operator  
**Implementation status:** adapter implemented; source disabled by default  
**Operational approval:** requires the operator to accept/recheck the current
Duffel Services Agreement and set explicit approval configuration  
**Adapter code:** `DUFFEL`

## Source and method

- Provider: Duffel Technology Limited
- Source type: documented flight-offer API / OTA aggregation platform
- Base URL: `https://api.duffel.com`
- Endpoint scope: `POST /air/offer_requests`
- Collection method: authenticated HTTPS JSON API; no browser automation or scraping
- API version header: `Duffel-Version: v2`
- Authentication: bearer access token held only in backend environment secrets

Primary documentation reviewed:

- Offer Requests: https://duffel.com/docs/api/v2/offer-requests
- Test mode: https://duffel.com/docs/api/overview/test-mode
- Versioning: https://duffel.com/docs/api/overview/versioning
- Services Agreement: https://duffel.com/services-agreement
- Website terms: https://duffel.com/terms

## Data-class boundary

- Duffel test tokens return sandbox content with `live_mode=false`. The provider
  states that sandbox schedules and prices may be unrealistic. This project
  stores such results as `RECORDED_DEMO`, never `LIVE`.
- A response may be stored as `LIVE` only when `DUFFEL_LIVE_MODE=true`, the
  access token is a live token, the returned offer request declares
  `live_mode=true`, and `DUFFEL_SOURCE_APPROVED=true`.
- Missing or contradictory mode evidence fails closed.

## Query and operational limits

- One adult, one-way, economy, direct-only search.
- Exactly the configured route and travel date.
- `max_connections=0` and a configurable provider `supplier_timeout`.
- Sequential source execution with a conservative configurable request rate;
  default five requests per minute until the operator's agreement says otherwise.
- One initial attempt plus at most two transient retries with bounded backoff.
- Authentication, policy, parser, invalid-response, CAPTCHA, and no-result
  outcomes are not retried.

The provider agreement discusses commercial/search-to-order limits. Before
production use, the operator must confirm that statistical fare observation is
permitted for the account and configure a rate no higher than the agreement.

## Retention and attribution

The database retains a compact evidence projection only: provider offer/request
identifiers, live-mode marker, carrier and segment identifiers/times, currency,
base/tax/total amounts, expiry, and content hash. It does not retain access
tokens, passenger identity, cookies, payment data, or the complete response.

Duffel documentation requires operating-carrier identity when offers are shown
to consumers. The analytical UI must display the operating carrier for any
Duffel-derived observation and identify Duffel as the source.

## Known limitations

- A credential is required for every API call.
- Test mode cannot prove live prices.
- Production activation and the account-specific Services Agreement are
  external operator actions.
- Returned currency depends on the Duffel organisation configuration; non-INR
  offers are preserved as evidence but excluded by normalization.
- Offers expire quickly and represent observations, not guaranteed bookable
  prices at a later time.

## Approval decision

The documented API is the selected permissible technical integration path.
The source remains disabled and `PENDING_REVIEW` in seeded data until the
operator confirms the current account agreement and explicitly enables it.
This document is not legal advice and does not claim production account access.
