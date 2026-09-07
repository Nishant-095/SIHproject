from __future__ import annotations

import json
import string
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from app.collectors.base import FareSearchRequest

ALLOWED_FIELDS = {
    "airline_name",
    "carrier_code",
    "flight_number",
    "origin",
    "destination",
    "departure_time",
    "arrival_time",
    "currency",
    "base_fare",
    "taxes",
    "udf",
    "convenience_fee",
    "other_fees",
    "total_fare",
    "fare_class",
    "cabin_class",
    "is_nonstop",
    "availability",
}

REQUIRED_PROFILE_FIELDS = {
    "airline_name",
    "carrier_code",
    "flight_number",
    "origin",
    "destination",
    "departure_time",
    "arrival_time",
    "currency",
    "total_fare",
    "cabin_class",
    "is_nonstop",
    "availability",
}

ALLOWED_TEMPLATE_FIELDS = {
    "origin",
    "destination",
    "travel_date",
    "passenger_count",
    "cabin",
    "currency",
}


class FieldSelector(BaseModel):
    """How to read one value relative to a quote-card element."""

    selector: str | None = None
    attribute: str | None = None

    @model_validator(mode="after")
    def locator_is_not_empty(self) -> FieldSelector:
        if self.selector is not None and not self.selector.strip():
            raise ValueError("field selector cannot be blank")
        if self.attribute is not None and not self.attribute.strip():
            raise ValueError("field attribute cannot be blank")
        if self.selector is None and self.attribute is None:
            raise ValueError("field mapping requires a selector or attribute")
        return self


class WebExtractionProfile(BaseModel):
    """Versioned, declarative extraction rules for one permissioned portal."""

    profile_version: str = Field(min_length=1, max_length=80)
    source_code: Literal["PERMISSIONED_WEB"]
    source_name: str = Field(min_length=1, max_length=120)
    source_type: Literal["AIRLINE_DIRECT", "OTA"]
    base_url: str
    robots_url: str
    search_url_template: str
    quote_selector: str = Field(min_length=1, max_length=500)
    no_results_selector: str | None = Field(default=None, max_length=500)
    max_quotes: int = Field(default=50, ge=1, le=200)
    fields: dict[str, FieldSelector]

    @field_validator("base_url", "robots_url")
    @classmethod
    def validate_absolute_url(cls, value: str) -> str:
        _validate_web_url(value)
        return value.rstrip("/") if value.endswith("/") else value

    @model_validator(mode="after")
    def validate_contract(self) -> WebExtractionProfile:
        base = urlsplit(self.base_url)
        robots = urlsplit(self.robots_url)
        if (base.scheme, base.netloc) != (robots.scheme, robots.netloc):
            raise ValueError("robots_url must use the source base origin")

        unknown_fields = set(self.fields) - ALLOWED_FIELDS
        if unknown_fields:
            raise ValueError(f"unsupported extraction fields: {sorted(unknown_fields)}")
        missing_fields = REQUIRED_PROFILE_FIELDS - set(self.fields)
        if missing_fields:
            raise ValueError(f"missing required extraction fields: {sorted(missing_fields)}")

        formatter = string.Formatter()
        template_fields = {
            field_name
            for _, field_name, _, _ in formatter.parse(self.search_url_template)
            if field_name is not None
        }
        unknown_template_fields = template_fields - ALLOWED_TEMPLATE_FIELDS
        if unknown_template_fields:
            raise ValueError(f"unsupported search URL fields: {sorted(unknown_template_fields)}")
        if not {"origin", "destination", "travel_date"}.issubset(template_fields):
            raise ValueError("search URL must include origin, destination, and travel_date")
        example_url = self.build_search_url(
            FareSearchRequest(origin="DEL", destination="BOM", travel_date=_EXAMPLE_DATE)
        )
        target = urlsplit(example_url)
        if (base.scheme, base.netloc) != (target.scheme, target.netloc):
            raise ValueError("search_url_template must stay on the source base origin")
        return self

    def build_search_url(self, request: FareSearchRequest) -> str:
        values = {
            "origin": quote(request.origin, safe=""),
            "destination": quote(request.destination, safe=""),
            "travel_date": quote(request.travel_date.isoformat(), safe=""),
            "passenger_count": request.passenger_count,
            "cabin": quote(request.cabin, safe=""),
            "currency": quote(request.currency, safe=""),
        }
        url = self.search_url_template.format(**values)
        _validate_web_url(url)
        return url


def load_web_extraction_profile(path: Path) -> WebExtractionProfile:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read web extraction profile: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Web extraction profile is not valid JSON: {path}") from exc
    return WebExtractionProfile.model_validate(payload)


def _validate_web_url(value: str) -> None:
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("source URLs must be absolute and cannot contain credentials")
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return
    raise ValueError("source URLs must use HTTPS except for local verification")


_EXAMPLE_DATE = date(2099, 1, 1)
