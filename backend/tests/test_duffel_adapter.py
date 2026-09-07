from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from app.collectors.base import AdapterError, FareSearchRequest
from app.collectors.duffel import DuffelAdapter
from app.core.config import Settings
from app.domain.enums import FailureCode

FIXTURES = Path(__file__).parent / "fixtures" / "duffel"


def _fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def _request() -> FareSearchRequest:
    return FareSearchRequest(origin="DEL", destination="BOM", travel_date=date(2026, 9, 12))


def test_blank_environment_token_is_treated_as_unconfigured() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        duffel_access_token="  ",
    )
    assert settings.duffel_access_token is None


def test_normal_response_uses_frozen_request_and_compact_evidence() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_fixture("normal.json"))

    async def run() -> list:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DuffelAdapter(
                access_token="test-secret-token",
                expected_live_mode=False,
                client=client,
            )
            return await adapter.search(_request())

    quotes = asyncio.run(run())
    assert len(quotes) == 1
    quote = quotes[0]
    assert quote.flight_number == "AI2421"
    assert str(quote.total_fare) == "5250.00"
    assert quote.raw_payload["live_mode"] is False
    assert quote.raw_payload["provider"] == "DUFFEL"
    assert "test-secret-token" not in json.dumps(quote.raw_payload)

    request = captured["request"]
    assert isinstance(request, httpx.Request)
    assert request.headers["Duffel-Version"] == "v2"
    assert request.url.params["supplier_timeout"] == "20000"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["data"] == {
        "slices": [{"origin": "DEL", "destination": "BOM", "departure_date": "2026-09-12"}],
        "passengers": [{"type": "adult"}],
        "cabin_class": "economy",
        "max_connections": 0,
    }


def test_empty_and_missing_optional_responses_parse_without_fabrication() -> None:
    adapter = DuffelAdapter(access_token="token", expected_live_mode=False)
    assert adapter.parse_response(_fixture("empty.json")) == []
    quote = adapter.parse_response(_fixture("missing_optional.json"))[0]
    assert quote.base_fare is None
    assert quote.taxes is None
    assert quote.udf is None
    assert quote.total_fare is not None


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, FailureCode.AUTHENTICATION_FAILED),
        (403, FailureCode.AUTHENTICATION_FAILED),
        (429, FailureCode.RATE_LIMITED),
        (503, FailureCode.SOURCE_UNAVAILABLE),
        (422, FailureCode.INVALID_RESPONSE),
    ],
)
def test_http_failures_are_structured(status_code: int, expected: FailureCode) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"errors": []})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DuffelAdapter(access_token="token", expected_live_mode=False, client=client)
            with pytest.raises(AdapterError) as error:
                await adapter.search(_request())
            assert error.value.code is expected

    asyncio.run(run())


def test_malformed_and_mode_mismatch_fail_closed() -> None:
    adapter = DuffelAdapter(access_token="token", expected_live_mode=False)
    with pytest.raises(AdapterError) as malformed:
        adapter.parse_response(_fixture("malformed.json"))
    assert malformed.value.code is FailureCode.PARSER_CHANGED

    with pytest.raises(AdapterError) as missing_offers:
        adapter.parse_response({"data": {"live_mode": False}})
    assert missing_offers.value.code is FailureCode.PARSER_CHANGED

    live_adapter = DuffelAdapter(access_token="token", expected_live_mode=True)
    with pytest.raises(AdapterError) as mismatch:
        live_adapter.parse_response(_fixture("normal.json"))
    assert mismatch.value.code is FailureCode.INVALID_RESPONSE


def test_network_timeout_is_structured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("controlled", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DuffelAdapter(access_token="token", expected_live_mode=False, client=client)
            with pytest.raises(AdapterError) as error:
                await adapter.search(_request())
            assert error.value.code is FailureCode.NETWORK_TIMEOUT

    asyncio.run(run())
