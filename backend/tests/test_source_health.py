from __future__ import annotations

import asyncio
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.collectors.base import AdapterError, FareSearchRequest, RawFareQuote
from app.collectors.fixture import FixtureAdapter
from app.collectors.registry import AdapterRegistry
from app.core.config import Settings
from app.domain.enums import FailureCode, SourceHealthStatus
from app.services.collection import CollectionService


class PartlyUnavailableAdapter(FixtureAdapter):
    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        if request.origin == "DEL" and request.destination == "BOM":
            raise AdapterError(FailureCode.SOURCE_UNAVAILABLE, "controlled outage")
        return await super().search(request)


def test_source_failures_are_visible_in_source_health(
    client: TestClient,
    session: Session,
) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        adapter_max_retries=0,
    )
    asyncio.run(
        CollectionService(settings, AdapterRegistry([PartlyUnavailableAdapter()])).run_fixture(
            session,
            methodological_date=date(2026, 9, 15),
        )
    )

    response = client.get("/api/v1/sources/health")
    assert response.status_code == 200
    fixture = next(item for item in response.json() if item["source_code"] == "FIXTURE_LOCAL")
    assert fixture["health_status"] == SourceHealthStatus.DEGRADED.value
    assert fixture["successful_jobs"] == 10
    assert fixture["failed_jobs"] == 5
    assert fixture["success_rate"] == 66.67
    assert fixture["last_failure_code"] == FailureCode.SOURCE_UNAVAILABLE.value
    assert fixture["average_duration_ms"] is not None

    history = client.get("/api/v1/sources/health/history")
    assert history.status_code == 200
    point = next(item for item in history.json() if item["source_code"] == "FIXTURE_LOCAL")
    assert point["methodological_date"] == "2026-09-15"
    assert point["successful_jobs"] == 10
    assert point["failed_jobs"] == 5
    assert point["success_rate"] == 66.67
    assert point["health_status"] == SourceHealthStatus.DEGRADED.value
