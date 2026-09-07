from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.collectors.base import AdapterError
from app.collectors.web_profile import FieldSelector, WebExtractionProfile
from app.domain.enums import FailureCode

CAPTCHA_MARKERS = (
    "captcha",
    "verify you are human",
    "checking your browser",
    "challenge-platform",
    "cf-chl-",
    "are you a robot",
)
BLOCK_MARKERS = (
    "access denied",
    "request blocked",
    "automated access is prohibited",
)


@dataclass(frozen=True, slots=True)
class RenderedPage:
    final_url: str
    status_code: int
    page_title: str
    captured_at_utc: datetime
    cards: tuple[dict[str, str | None], ...]


class PageRenderer(Protocol):
    async def render(
        self,
        *,
        url: str,
        profile: WebExtractionProfile,
        user_agent: str,
        timeout_ms: int,
    ) -> RenderedPage:
        """Render a search page and return only configured fare fields."""


class PlaywrightPageRenderer:
    """Small headless Chromium boundary with no anti-bot circumvention."""

    async def render(
        self,
        *,
        url: str,
        profile: WebExtractionProfile,
        user_agent: str,
        timeout_ms: int,
    ) -> RenderedPage:
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=["--disable-dev-shm-usage"],
                )
                try:
                    context = await browser.new_context(
                        user_agent=user_agent,
                        locale="en-IN",
                        timezone_id="Asia/Kolkata",
                    )
                    page = await context.new_page()
                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                    status_code = 0 if response is None else response.status
                    self._ensure_same_origin(url, page.url)
                    await self._raise_for_page_failure(page, status_code)
                    await self._wait_for_result(page, profile, timeout_ms)
                    cards = await self._extract_cards(page, profile)
                    return RenderedPage(
                        final_url=page.url,
                        status_code=status_code,
                        page_title=await page.title(),
                        captured_at_utc=datetime.now(UTC),
                        cards=cards,
                    )
                finally:
                    await browser.close()
        except AdapterError:
            raise
        except PlaywrightTimeoutError as exc:
            raise AdapterError(
                FailureCode.NETWORK_TIMEOUT,
                "Permissioned web source timed out",
            ) from exc
        except PlaywrightError as exc:
            raise AdapterError(
                FailureCode.SOURCE_UNAVAILABLE,
                "Permissioned web browser collection failed",
            ) from exc

    @staticmethod
    async def _raise_for_page_failure(page: Page, status_code: int) -> None:
        content = (await page.content()).lower()
        if any(marker in content for marker in CAPTCHA_MARKERS):
            raise AdapterError(
                FailureCode.CAPTCHA_BLOCKED,
                "Source presented a CAPTCHA or browser challenge; no bypass attempted",
            )
        if status_code == 429:
            raise AdapterError(FailureCode.RATE_LIMITED, "Source returned HTTP 429")
        if status_code >= 500:
            raise AdapterError(
                FailureCode.SOURCE_UNAVAILABLE,
                f"Source returned HTTP {status_code}",
            )
        if status_code >= 400 or any(marker in content for marker in BLOCK_MARKERS):
            raise AdapterError(
                FailureCode.SOURCE_UNAVAILABLE,
                f"Source blocked or rejected collection (HTTP {status_code})",
            )

    @staticmethod
    async def _wait_for_result(
        page: Page,
        profile: WebExtractionProfile,
        timeout_ms: int,
    ) -> None:
        quote = page.locator(profile.quote_selector)
        if await quote.count() > 0:
            return
        no_results = (
            None
            if profile.no_results_selector is None
            else page.locator(profile.no_results_selector)
        )
        if no_results is not None and await no_results.count() > 0:
            return
        try:
            await page.wait_for_function(
                """([quoteSelector, emptySelector]) =>
                    document.querySelector(quoteSelector) !== null ||
                    (emptySelector !== null && document.querySelector(emptySelector) !== null)
                """,
                arg=[profile.quote_selector, profile.no_results_selector],
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            content = (await page.content()).lower()
            if any(marker in content for marker in CAPTCHA_MARKERS):
                raise AdapterError(
                    FailureCode.CAPTCHA_BLOCKED,
                    "Source presented a CAPTCHA or browser challenge; no bypass attempted",
                ) from exc
            raise AdapterError(
                FailureCode.PARSER_CHANGED,
                "Neither fare results nor the configured no-results marker appeared",
            ) from exc

    @classmethod
    async def _extract_cards(
        cls,
        page: Page,
        profile: WebExtractionProfile,
    ) -> tuple[dict[str, str | None], ...]:
        card_locator = page.locator(profile.quote_selector)
        count = await card_locator.count()
        if count > profile.max_quotes:
            raise AdapterError(
                FailureCode.INVALID_RESPONSE,
                f"Source returned more than the configured {profile.max_quotes} quotes",
            )
        cards: list[dict[str, str | None]] = []
        for index in range(count):
            card = card_locator.nth(index)
            fields = {
                name: await cls._read_field(card, locator)
                for name, locator in profile.fields.items()
            }
            cards.append(fields)
        return tuple(cards)

    @staticmethod
    async def _read_field(card: Locator, field: FieldSelector) -> str | None:
        target = card if field.selector is None else card.locator(field.selector).first
        if await target.count() == 0:
            return None
        value = (
            await target.get_attribute(field.attribute)
            if field.attribute is not None
            else await target.inner_text()
        )
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _ensure_same_origin(requested_url: str, final_url: str) -> None:
        requested = urlsplit(requested_url)
        final = urlsplit(final_url)
        if (requested.scheme, requested.netloc) != (final.scheme, final.netloc):
            raise AdapterError(
                FailureCode.INVALID_RESPONSE,
                "Source redirected collection outside its approved origin",
            )
