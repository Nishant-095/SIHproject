import asyncio
from datetime import date

from app.collectors.base import FareSearchRequest
from app.collectors.fixture import FixtureAdapter


def test_fixture_adapter_is_deterministic_and_honest() -> None:
    adapter = FixtureAdapter()
    request = FareSearchRequest(origin="DEL", destination="BOM", travel_date=date(2026, 9, 12))
    first = asyncio.run(adapter.search(request))
    second = asyncio.run(adapter.search(request))

    assert first == second
    assert len(first) == 2
    assert all(quote.raw_payload["fixture"] is True for quote in first)
    assert all(quote.currency == "INR" for quote in first)
    assert all(quote.total_fare and quote.total_fare > 0 for quote in first)
