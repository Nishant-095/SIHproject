from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from web_profile_helpers import valid_card, web_profile

from app.collectors.base import FareSearchRequest, FareSourceAdapter, RawFareQuote
from app.collectors.duffel import DuffelAdapter
from app.collectors.fixture import FixtureAdapter
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.web_browser import RenderedPage
from app.collectors.web_compliance import RobotsEvidence

DUFFEL_FIXTURE = Path(__file__).parent / "fixtures" / "duffel" / "normal.json"


class ContractRenderer:
    async def render(self, *, url: str, profile, user_agent: str, timeout_ms: int):
        return RenderedPage(
            final_url=url,
            status_code=200,
            page_title="Approved source",
            captured_at_utc=datetime(2099, 1, 1, tzinfo=UTC),
            cards=(valid_card(),),
        )


class ContractRobotsChecker:
    async def check(self, *, robots_url: str, target_url: str, user_agent: str):
        return RobotsEvidence(robots_url, 200, True, None)


async def _collect_all(request: FareSearchRequest) -> list[tuple[str, list[RawFareQuote]]]:
    payload = json.loads(DUFFEL_FIXTURE.read_text(encoding="utf-8"))

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapters: list[FareSourceAdapter] = [
            FixtureAdapter(),
            DuffelAdapter(
                access_token="contract-test-token",
                expected_live_mode=False,
                client=client,
            ),
            PermissionedWebAdapter(
                profile=web_profile(),
                permission_confirmed=True,
                permission_reference="contract-test-approval",
                user_agent="AirfareAPIxContractTest/1.0",
                browser_timeout_ms=5_000,
                renderer=ContractRenderer(),
                robots_checker=ContractRobotsChecker(),
            ),
        ]
        return [(adapter.source_code, await adapter.search(request)) for adapter in adapters]


def test_same_search_contract_works_across_three_provider_adapters() -> None:
    request = FareSearchRequest(
        origin="DEL",
        destination="BOM",
        travel_date=date(2099, 1, 8),
    )
    results = asyncio.run(_collect_all(request))

    assert [source for source, _ in results] == [
        "FIXTURE_LOCAL",
        "DUFFEL",
        "PERMISSIONED_WEB",
    ]
    for _, quotes in results:
        assert quotes
        quote = quotes[0]
        assert isinstance(quote, RawFareQuote)
        assert quote.currency == "INR"
        assert quote.total_fare is not None and quote.total_fare > 0
        assert quote.flight_number
        assert quote.is_nonstop is True
        assert quote.raw_payload
