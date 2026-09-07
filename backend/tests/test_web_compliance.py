from __future__ import annotations

import asyncio

import httpx
import pytest

from app.collectors.base import AdapterError
from app.collectors.web_compliance import HttpRobotsChecker
from app.domain.enums import FailureCode


def _run_check(body: str, status_code: int = 200):
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(status_code, text=body)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            checker = HttpRobotsChecker(client)
            first = await checker.check(
                robots_url="https://portal.example.com/robots.txt",
                target_url="https://portal.example.com/search?origin=DEL",
                user_agent="AirfareAPIxResearchBot/0.1",
            )
            second = await checker.check(
                robots_url="https://portal.example.com/robots.txt",
                target_url="https://portal.example.com/search?origin=BOM",
                user_agent="AirfareAPIxResearchBot/0.1",
            )
            return first, second

    return asyncio.run(run()), lambda: requests


def test_robots_allow_and_cache_are_enforced() -> None:
    decisions, request_count = _run_check("User-agent: *\nAllow: /search\nCrawl-delay: 3\n")
    assert all(decision.allowed for decision in decisions)
    assert decisions[0].crawl_delay_seconds == 3
    assert request_count() == 1


def test_missing_robots_is_allowed_only_after_permission_gate() -> None:
    decisions, _ = _run_check("", status_code=404)
    assert decisions[0].allowed is True
    assert decisions[0].status_code == 404


def test_robots_cross_origin_redirect_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "portal.example.com":
            return httpx.Response(302, headers={"Location": "https://other.example/robots.txt"})
        return httpx.Response(200, text="User-agent: *\nAllow: /\n")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await HttpRobotsChecker(client).check(
                robots_url="https://portal.example.com/robots.txt",
                target_url="https://portal.example.com/search",
                user_agent="AirfareAPIxResearchBot/0.1",
            )

    with pytest.raises(AdapterError) as error:
        asyncio.run(run())
    assert error.value.code is FailureCode.INVALID_RESPONSE


@pytest.mark.parametrize(
    ("body", "status_code", "failure"),
    [
        ("User-agent: *\nDisallow: /search\n", 200, FailureCode.ROBOTS_DISALLOWED),
        ("", 403, FailureCode.ROBOTS_DISALLOWED),
        ("", 429, FailureCode.RATE_LIMITED),
        ("", 503, FailureCode.SOURCE_UNAVAILABLE),
    ],
)
def test_robots_failures_are_structured(
    body: str,
    status_code: int,
    failure: FailureCode,
) -> None:
    with pytest.raises(AdapterError) as error:
        _run_check(body, status_code)
    assert error.value.code is failure
