from __future__ import annotations

import pytest
from pydantic import ValidationError
from web_profile_helpers import web_profile

from app.collectors.web_profile import WebExtractionProfile


def test_profile_refuses_cross_origin_search_and_robots_urls() -> None:
    payload = web_profile().model_dump(mode="json")
    payload["robots_url"] = "https://other.example.com/robots.txt"
    with pytest.raises(ValidationError, match="robots_url must use the source base origin"):
        WebExtractionProfile.model_validate(payload)

    payload = web_profile().model_dump(mode="json")
    payload["search_url_template"] = (
        "https://other.example.com/search?origin={origin}&destination={destination}"
        "&date={travel_date}"
    )
    with pytest.raises(ValidationError, match="search_url_template must stay"):
        WebExtractionProfile.model_validate(payload)


def test_profile_refuses_credentials_and_unmapped_fields() -> None:
    payload = web_profile().model_dump(mode="json")
    payload["base_url"] = "https://user:secret@portal.example.com"
    with pytest.raises(ValidationError, match="cannot contain credentials"):
        WebExtractionProfile.model_validate(payload)

    payload = web_profile().model_dump(mode="json")
    payload["fields"]["total_fare"] = {}
    with pytest.raises(ValidationError, match="requires a selector or attribute"):
        WebExtractionProfile.model_validate(payload)


def test_profile_refuses_unknown_template_inputs() -> None:
    payload = web_profile().model_dump(mode="json")
    payload["search_url_template"] += "&token={secret}"
    with pytest.raises(ValidationError, match="unsupported search URL fields"):
        WebExtractionProfile.model_validate(payload)
