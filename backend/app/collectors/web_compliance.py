from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.collectors.base import AdapterError
from app.domain.enums import FailureCode


@dataclass(frozen=True, slots=True)
class RobotsEvidence:
    robots_url: str
    status_code: int
    allowed: bool
    crawl_delay_seconds: float | None


class RobotsChecker(Protocol):
    async def check(self, *, robots_url: str, target_url: str, user_agent: str) -> RobotsEvidence:
        """Return an explicit robots decision or raise a structured failure."""


class HttpRobotsChecker:
    """Fetch and enforce robots.txt before every distinct source profile is used."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._cache: dict[str, tuple[int, RobotFileParser | None]] = {}

    async def check(
        self,
        *,
        robots_url: str,
        target_url: str,
        user_agent: str,
    ) -> RobotsEvidence:
        status_code, parser = await self._robots_parser(robots_url, user_agent)
        allowed = parser is None or parser.can_fetch(user_agent, target_url)
        delay = None if parser is None else parser.crawl_delay(user_agent)
        if not allowed:
            raise AdapterError(
                FailureCode.ROBOTS_DISALLOWED,
                "Source robots.txt disallows the configured search URL",
            )
        return RobotsEvidence(
            robots_url=robots_url,
            status_code=status_code,
            allowed=True,
            crawl_delay_seconds=None if delay is None else float(delay),
        )

    async def _robots_parser(
        self,
        robots_url: str,
        user_agent: str,
    ) -> tuple[int, RobotFileParser | None]:
        if robots_url in self._cache:
            return self._cache[robots_url]
        try:
            if self._client is not None:
                response = await self._client.get(
                    robots_url,
                    headers={"User-Agent": user_agent, "Accept": "text/plain"},
                    follow_redirects=True,
                )
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(
                        robots_url,
                        headers={"User-Agent": user_agent, "Accept": "text/plain"},
                    )
        except httpx.TimeoutException as exc:
            raise AdapterError(
                FailureCode.NETWORK_TIMEOUT,
                "Timed out while checking source robots.txt",
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterError(
                FailureCode.SOURCE_UNAVAILABLE,
                "Could not check source robots.txt",
            ) from exc

        expected_origin = urlsplit(robots_url)
        final_origin = urlsplit(str(response.url))
        if (expected_origin.scheme, expected_origin.netloc) != (
            final_origin.scheme,
            final_origin.netloc,
        ):
            raise AdapterError(
                FailureCode.INVALID_RESPONSE,
                "Source robots.txt redirected outside its approved origin",
            )

        if response.status_code in {401, 403}:
            raise AdapterError(
                FailureCode.ROBOTS_DISALLOWED,
                f"Source robots.txt returned HTTP {response.status_code}",
            )
        if response.status_code == 429:
            raise AdapterError(FailureCode.RATE_LIMITED, "Source robots.txt was rate limited")
        if response.status_code >= 500:
            raise AdapterError(
                FailureCode.SOURCE_UNAVAILABLE,
                f"Source robots.txt returned HTTP {response.status_code}",
            )
        result: tuple[int, RobotFileParser | None]
        if response.status_code == 404:
            result = (response.status_code, None)
        elif response.status_code >= 400:
            raise AdapterError(
                FailureCode.INVALID_RESPONSE,
                f"Source robots.txt returned HTTP {response.status_code}",
            )
        else:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            result = (response.status_code, parser)
        self._cache[robots_url] = result
        return result
