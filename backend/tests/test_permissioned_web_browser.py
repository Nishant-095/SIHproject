from __future__ import annotations

import asyncio
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from web_profile_helpers import web_profile

from app.collectors.base import AdapterError, FareSearchRequest
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.domain.enums import FailureCode

FIXTURE_HTML = (
    Path(__file__).parent / "fixtures" / "permissioned_web" / "search.html"
).read_text(encoding="utf-8")


class DynamicPortalHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/robots.txt":
            self._respond("text/plain", "User-agent: *\nAllow: /search\n")
            return
        if parsed.path != "/search":
            self.send_error(404)
            return
        query = parse_qs(parsed.query)
        origin = query.get("origin", [""])[0]
        destination = query.get("destination", [""])[0]
        travel_date = query.get("date", [""])[0]
        if origin == "CAP":
            self._respond("text/html", "<html><body>Verify you are human CAPTCHA</body></html>")
            return
        if origin == "EMPTY":
            self._respond(
                "text/html",
                "<html><body><div data-no-flight-results></div></body></html>",
            )
            return
        if origin == "ERROR":
            self._respond("text/html", "<html><body>temporarily unavailable</body></html>", 503)
            return
        body = (
            FIXTURE_HTML.replace("__ORIGIN__", origin)
            .replace("__DESTINATION__", destination)
            .replace("__TRAVEL_DATE__", travel_date)
        )
        self._respond("text/html", body)

    def _respond(self, content_type: str, body: str, status: int = 200) -> None:
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def dynamic_portal() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DynamicPortalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _adapter(base_url: str) -> PermissionedWebAdapter:
    return PermissionedWebAdapter(
        profile=web_profile(base_url),
        permission_confirmed=True,
        permission_reference="local-browser-contract-test",
        user_agent="AirfareAPIxResearchBot/0.1",
        browser_timeout_ms=5_000,
    )


@pytest.mark.browser
def test_real_chromium_renders_javascript_and_extracts_fare(dynamic_portal: str) -> None:
    quotes = asyncio.run(
        _adapter(dynamic_portal).search(
            FareSearchRequest(
                origin="DEL",
                destination="BOM",
                travel_date=date(2099, 1, 8),
            )
        )
    )
    assert len(quotes) == 1
    assert quotes[0].flight_number == "AI2421"
    assert str(quotes[0].total_fare) == "5250.00"
    assert quotes[0].raw_payload["page"]["status_code"] == 200


@pytest.mark.browser
def test_real_chromium_detects_captcha_and_does_not_bypass_it(dynamic_portal: str) -> None:
    with pytest.raises(AdapterError) as error:
        asyncio.run(
            _adapter(dynamic_portal).search(
                FareSearchRequest(
                    origin="CAP",
                    destination="BOM",
                    travel_date=date(2099, 1, 8),
                )
            )
        )
    assert error.value.code is FailureCode.CAPTCHA_BLOCKED


@pytest.mark.browser
def test_real_chromium_handles_no_results_without_fabricating_a_quote(
    dynamic_portal: str,
) -> None:
    quotes = asyncio.run(
        _adapter(dynamic_portal).search(
            FareSearchRequest(
                origin="EMPTY",
                destination="BOM",
                travel_date=date(2099, 1, 8),
            )
        )
    )
    assert quotes == []


@pytest.mark.browser
def test_real_chromium_maps_source_unavailable_to_structured_failure(
    dynamic_portal: str,
) -> None:
    with pytest.raises(AdapterError) as error:
        asyncio.run(
            _adapter(dynamic_portal).search(
                FareSearchRequest(
                    origin="ERROR",
                    destination="BOM",
                    travel_date=date(2099, 1, 8),
                )
            )
        )
    assert error.value.code is FailureCode.SOURCE_UNAVAILABLE
