# Web Collection Candidate Review

**Review date:** 2026-09-05  
**Decision:** no public airline/OTA website reviewed below is approved for live collection.

The SIH26056 statement asks for a robust multi-source extraction engine, but it
does not grant permission to copy data from third-party websites. Each source's
own terms and access rules still apply.

| Candidate | Evidence reviewed | Result |
|---|---|---|
| Air India | [Terms](https://www.airindia.com/in/en/terms-and-condition.html) prohibit automated scraping/copying without express written permission | `RESTRICTED` without written permission |
| Akasa Air | [Terms](https://www.akasaair.com/quick-links/terms-and-conditions) limit use and copying/replication without prior written permission; robots alone is not permission | `RESTRICTED` without written permission |
| SpiceJet | [Disclaimer](https://corporate.spicejet.com/Disclaimer.aspx) restricts copying/processing site content; robots also restrict API paths | `RESTRICTED` |
| Air India Express | [Robots rules](https://www.airindiaexpress.com/robots.txt) restrict the flight-availability path | `ROBOTS_DISALLOWED` for the relevant path |
| IndiGo | [Flight-booking terms](https://www.goindigo.in/information/terms-and-conditions.html) forbid copying or selling website information without prior written permission | `RESTRICTED` without written permission |

## Approval gate

The implemented `PERMISSIONED_WEB` adapter can be configured for exactly one
source only after the operator has:

1. written permission or another clear contractual basis for the intended use;
2. a saved permission/review reference;
3. a same-origin versioned extraction profile;
4. a fresh terms and `robots.txt` review;
5. an approved request rate and retention policy.

Until then it remains disabled and creates no external requests. Fixtures and
the local JavaScript portal test prove the engine, not permission or genuine
airfare data.
